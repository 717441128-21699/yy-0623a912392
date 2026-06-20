import csv
import os
from .parser import (
    parse_single_member,
    parse_and_validate_material,
    parse_and_validate_bracket,
    parse_and_validate_loads,
    parse_value_with_unit,
    ValidationError,
    REQUIRED_MATERIAL_FIELDS,
    REQUIRED_BRACKET_FIELDS,
)
from .materials import (
    get_steel_pipe_params,
    get_wood_joist_params,
    get_main_beam_params,
    get_fastener_params,
)


CSV_COLUMN_MAP = {
    "构件名称": "构件名称",
    "构件类型": "构件类型",

    "梁宽": "梁宽",
    "梁高": "梁高",
    "混凝土厚度": "混凝土厚度",
    "板厚": "混凝土厚度",

    "立杆纵距": "立杆纵距",
    "立杆横距": "立杆横距",
    "步距": "步距",
    "次楞间距": "次楞间距",
    "主楞间距": "主楞间距",
    "扫地杆高度": "扫地杆高度",

    "立杆钢管": "立杆钢管",
    "次楞木方": "次楞木方",
    "主楞类型": "主楞类型",
    "扣件类型": "扣件类型",

    "施工活荷载": "施工活荷载",
    "活荷载": "施工活荷载",
    "振捣荷载": "振捣荷载",
    "模板自重": "模板自重",

    "支撑高度": "支撑高度",
    "支模高度": "支撑高度",

    "模板类型": "模板类型",
    "模板厚度": "模板厚度",
}


CSV_MATERIAL_KEYS = ["立杆钢管", "次楞木方", "主楞类型", "扣件类型"]
CSV_BRACKET_KEYS = ["立杆纵距", "立杆横距", "步距", "次楞间距", "主楞间距", "扫地杆高度"]
CSV_LOAD_KEYS_SLAB = ["混凝土厚度", "施工活荷载", "振捣荷载", "模板自重"]
CSV_LOAD_KEYS_BEAM = ["梁宽", "梁高", "施工活荷载", "振捣荷载", "模板自重"]


def _detect_delimiter(line):
    if "\t" in line:
        return "\t"
    if "|" in line:
        return "|"
    if "," in line:
        return ","
    if ";" in line:
        return ";"
    return None


def _normalize_row(row, headers):
    normalized = {}
    n_headers = len(headers)
    n_cells = len(row)

    if n_cells == n_headers:
        pairs = list(zip(headers, row))
    elif n_cells > n_headers:
        pairs = list(zip(headers, row[:n_headers]))
    else:
        padded_row = row + [""] * (n_headers - n_cells)
        pairs = list(zip(headers, padded_row))

    for header, cell in pairs:
        raw_header = header.strip()
        value = cell.strip()
        mapped_key = CSV_COLUMN_MAP.get(raw_header, raw_header)
        if value:
            normalized[mapped_key] = value
    return normalized


def _build_member_dict(normalized_row, defaults):
    member = dict(defaults) if defaults else {}

    for key, value in normalized_row.items():
        if key in CSV_MATERIAL_KEYS:
            if "材料规格" not in member:
                member["材料规格"] = {}
            member["材料规格"][key] = value
        elif key in CSV_BRACKET_KEYS:
            if "支架布置" not in member:
                member["支架布置"] = {}
            member["支架布置"][key] = value
        elif key in CSV_LOAD_KEYS_SLAB or key in CSV_LOAD_KEYS_BEAM:
            if "荷载参数" not in member:
                member["荷载参数"] = {}
            member["荷载参数"][key] = value
        else:
            member[key] = value

    if "材料规格" in member and "材料规格" in defaults:
        merged = dict(defaults["材料规格"])
        merged.update(member["材料规格"])
        member["材料规格"] = merged

    if "支架布置" in member and "支架布置" in defaults:
        merged = dict(defaults["支架布置"])
        merged.update(member["支架布置"])
        member["支架布置"] = merged

    if "荷载参数" in member and "荷载参数" in defaults:
        merged = dict(defaults["荷载参数"])
        merged.update(member["荷载参数"])
        member["荷载参数"] = merged

    return member


def parse_csv_file(filepath):
    """
    解析CSV或表格式文本文件，逐行校验，不中断。
    返回: (project_info, members, errors, warnings)
        project_info: dict, 工程信息
        members: list, 成功解析的构件列表
        errors: list of dict, 错误信息，每项包含 {行号, 构件名, 错误}
        warnings: list, 警告信息
    """
    if not os.path.exists(filepath):
        raise ValidationError(f"文件不存在: {filepath}")

    errors = []
    warnings = []
    members = []
    project_info = {
        "工程名称": os.path.splitext(os.path.basename(filepath))[0],
        "计算人": "",
        "计算日期": "",
        "模式": "batch",
        "验算项目": ["立杆承载力", "扣件抗滑", "次楞挠度", "主楞强度"],
    }

    defaults = {}

    with open(filepath, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    if not lines:
        raise ValidationError("文件为空")

    content_lines = []
    raw_line_numbers = []
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("//"):
            if stripped.startswith("#工程名称:") or stripped.startswith("# 工程名称:"):
                val = stripped.split(":", 1)[1].strip()
                project_info["工程名称"] = val
            elif stripped.startswith("#计算人:") or stripped.startswith("# 计算人:"):
                val = stripped.split(":", 1)[1].strip()
                project_info["计算人"] = val
            elif stripped.startswith("#计算日期:") or stripped.startswith("# 计算日期:"):
                val = stripped.split(":", 1)[1].strip()
                project_info["计算日期"] = val
            elif stripped.startswith("#默认") or stripped.startswith("# 默认"):
                pass
            continue
        content_lines.append(stripped)
        raw_line_numbers.append(line_no)

    if len(content_lines) < 2:
        raise ValidationError("文件内容不足，至少需要表头和一行数据")

    header_idx = None
    for i, line in enumerate(content_lines):
        first_col = line.split(",")[0].strip() if "," in line else (line.split("\t")[0].strip() if "\t" in line else (line.split("|")[0].strip() if "|" in line else (line.split(";")[0].strip() if ";" in line else line.strip())))
        if first_col in ("构件名称", "构件名", "构件编号"):
            header_idx = i
            break

    if header_idx is None:
        raise ValidationError(
            "找不到表头行，表头第一列必须是'构件名称'。请检查文件格式或使用竖线(|)等分隔符。"
        )

    header_line = content_lines[header_idx]
    delimiter = _detect_delimiter(header_line)

    if delimiter is None:
        raise ValidationError(
            "无法识别分隔符，请使用逗号(,)、制表符(Tab)、竖线(|)或分号(;)作为列分隔符"
        )

    headers = [h.strip() for h in header_line.split(delimiter)]
    headers = [h for h in headers if h]

    if not headers:
        raise ValidationError("表头为空")

    default_row = None
    for i in range(header_idx):
        line = content_lines[i]
        first_col = line.split(delimiter)[0].strip()
        if first_col in ("默认值", "默认", "DEFAULT", "default", "Defaults"):
            default_row = [c.strip() for c in line.split(delimiter)]
            break

    if default_row is not None:
        default_normalized = _normalize_row(default_row[1:], headers[1:])
        defaults = _build_member_dict(default_normalized, {})

    data_start_idx = header_idx + 1

    for row_idx in range(data_start_idx, len(content_lines)):
        line = content_lines[row_idx]
        actual_line_no = raw_line_numbers[row_idx]

        raw_cells = [c.strip() for c in line.split(delimiter)]

        if len(raw_cells) < 2:
            errors.append({
                "行号": actual_line_no,
                "构件名": raw_cells[0] if raw_cells else "",
                "错误": "列数不足"
            })
            continue

        normalized = _normalize_row(raw_cells, headers)
        member_name = normalized.get("构件名称", f"第{actual_line_no}行")
        member_dict = _build_member_dict(normalized, defaults)

        if "构件名称" not in member_dict:
            member_dict["构件名称"] = member_name

        try:
            member_dict["工程名称"] = project_info["工程名称"]
            parsed, member_warnings = parse_single_member(member_dict)
            for w in member_warnings:
                warnings.append(f"[{member_name}] {w}")
            members.append(parsed)
        except ValidationError as e:
            errors.append({
                "行号": actual_line_no,
                "构件名": member_name,
                "错误": str(e)
            })

    project_info["构件列表"] = members

    return project_info, members, errors, warnings
