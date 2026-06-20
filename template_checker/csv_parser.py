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
    "构件名": "构件名称",
    "构件编号": "构件名称",
    "编号": "构件名称",
    "名称": "构件名称",

    "构件类型": "构件类型",
    "类型": "构件类型",
    "构件": "构件类型",

    "梁宽": "梁宽",
    "梁高": "梁高",
    "混凝土厚度": "混凝土厚度",
    "板厚": "混凝土厚度",
    "厚度": "混凝土厚度",
    "砼厚": "混凝土厚度",
    "h": "混凝土厚度",

    "立杆纵距": "立杆纵距",
    "纵距": "立杆纵距",
    "立杆横距": "立杆横距",
    "横距": "立杆横距",
    "步距": "步距",
    "次楞间距": "次楞间距",
    "次楞": "次楞间距",
    "主楞间距": "主楞间距",
    "主楞跨距": "主楞间距",
    "扫地杆高度": "扫地杆高度",

    "立杆钢管": "立杆钢管",
    "钢管": "立杆钢管",
    "立杆": "立杆钢管",
    "钢管规格": "立杆钢管",
    "立杆规格": "立杆钢管",
    "次楞木方": "次楞木方",
    "木方": "次楞木方",
    "次楞规格": "次楞木方",
    "主楞类型": "主楞类型",
    "主楞": "主楞类型",
    "主楞规格": "主楞类型",
    "扣件类型": "扣件类型",
    "扣件": "扣件类型",

    "梁截面尺寸": "梁截面尺寸",
    "梁截面": "梁截面尺寸",
    "梁尺寸": "梁截面尺寸",
    "截面尺寸": "梁截面尺寸",

    "施工活荷载": "施工活荷载",
    "活荷载": "施工活荷载",
    "活载": "施工活荷载",
    "振捣荷载": "振捣荷载",
    "振捣": "振捣荷载",
    "模板自重": "模板自重",
    "模板": "模板自重",

    "支撑高度": "支撑高度",
    "支模高度": "支撑高度",
    "模板高度": "支撑高度",
    "架高": "支撑高度",

    "模板类型": "模板类型",
    "模板厚度": "模板厚度",

    "备注": "备注",
    "说明": "备注",
    "comment": "备注",
    "remark": "备注",
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


def _build_header_field_map(headers):
    """
    根据表头列表构建 "原始表头 -> 标准字段映射。自动识别空表头自动跳过，识别到的别名自动映射到标准字段。

    返回: (field_to_idx: dict, key=标准字段名 -> value=列索引
            unknown_headers: list, 未识别的表头文本列表
    """
    field_to_idx = {}
    unknown_headers = []
    for idx, raw_header in enumerate(headers):
        h = raw_header.strip()
        if not h:
            continue
        mapped = CSV_COLUMN_MAP.get(h)
        if mapped and mapped != "备注":
            if mapped not in field_to_idx:
                field_to_idx[mapped] = idx
        elif mapped != "备注":
            unknown_headers.append(h)
    return field_to_idx, unknown_headers


def _extract_values(raw_cells, field_to_idx):
    """根据字段->索引映射，从行单元格中提取字段值"""
    normalized = {}
    for field, idx in field_to_idx.items():
        if idx < len(raw_cells):
            value = raw_cells[idx].strip()
            if value:
                normalized[field] = value
    return normalized


def _build_member_dict(normalized_row, defaults):
    member = dict(defaults) if defaults else {}

    if "梁截面尺寸" in normalized_row and ("梁宽" not in normalized_row or "梁高" not in normalized_row):
        sec = normalized_row["梁截面尺寸"]
        import re
        m = re.match(r"\s*(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*", str(sec))
        if m:
            if "梁宽" not in normalized_row:
                normalized_row["梁宽"] = m.group(1) + "mm"
            if "梁高" not in normalized_row:
                normalized_row["梁高"] = m.group(2) + "mm"

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
    解析CSV或表格式文本文件，逐行校验，不中断。支持任意表头顺序、自动跳过空列。
    返回: (project_info, members, errors, warnings, preview)
        project_info: dict, 工程信息
        members: list, 成功解析的构件列表
        errors: list of dict, 错误信息，每项包含 {行号, 构件名, 错误}
        warnings: list, 警告信息
        preview: dict, 预览汇总，包含:
            - 总行数: 数据行数
            - 识别构件数: 成功解析的构件数
            - 错误行数: 参数错误行数
            - 楼板数: 楼板构件数
            - 梁数: 梁构件数
            - 识别字段: 成功识别的字段列表
            - 未知表头: 未识别的表头列表
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
            continue
        content_lines.append(stripped)
        raw_line_numbers.append(line_no)

    if len(content_lines) < 2:
        raise ValidationError("文件内容不足，至少需要表头和一行数据")

    header_idx = None
    delimiter = None

    for i, line in enumerate(content_lines):
        delim = _detect_delimiter(line)
        if not delim:
            continue
        cells = [c.strip() for c in line.split(delim)]
        if cells and cells[0] in ("构件名称", "构件名", "构件编号", "名称", "编号", "默认值", "默认", "DEFAULT", "default"):
            if cells[0] in ("构件名称", "构件名", "构件编号", "名称", "编号"):
                header_idx = i
                delimiter = delim
                break

    if header_idx is None:
        raise ValidationError(
            "找不到表头行（第一列必须是'构件名称'或其别名）。请检查文件格式。")

    header_line = content_lines[header_idx]
    if delimiter is None:
        delimiter = _detect_delimiter(header_line)

    raw_headers = [h.strip() for h in header_line.split(delimiter)]

    field_to_idx, unknown_headers = _build_header_field_map(raw_headers)

    if "构件名称" not in field_to_idx:
        raise ValidationError("表头中找不到'构件名称'或其别名（构件名/构件编号/名称/编号）")

    default_dict = {}
    for i in range(header_idx):
        line = content_lines[i]
        delim = _detect_delimiter(line) or delimiter
        cells = [c.strip() for c in line.split(delim)]
        if cells and cells[0] in ("默认值", "默认", "DEFAULT", "default", "Defaults"):
            default_values = _extract_values(cells, field_to_idx)
            if "构件名称" in default_values:
                del default_values["构件名称"]
            default_dict = _build_member_dict(default_values, {})
            break

    data_start_idx = header_idx + 1

    slab_count = 0
    beam_count = 0

    for row_idx in range(data_start_idx, len(content_lines)):
        line = content_lines[row_idx]
        actual_line_no = raw_line_numbers[row_idx]

        raw_cells = [c.strip() for c in line.split(delimiter)]

        if not raw_cells or all(not c for c in raw_cells):
            continue

        normalized = _extract_values(raw_cells, field_to_idx)
        member_name = normalized.get("构件名称", f"第{actual_line_no}行")

        if not normalized or (len(normalized) == 1 and "构件名称" in normalized):
            errors.append({
                "行号": actual_line_no,
                "构件名": member_name,
                "错误": "该行无可识别的有效参数，可能全为空行或格式错误"
            })
            continue

        member_dict = _build_member_dict(normalized, default_dict)

        if "构件名称" not in member_dict:
            member_dict["构件名称"] = member_name

        try:
            member_dict["工程名称"] = project_info["工程名称"]
            parsed, member_warnings = parse_single_member(member_dict)
            for w in member_warnings:
                warnings.append(f"[{member_name}] {w}")
            members.append(parsed)
            if parsed.get("构件类型") == "楼板":
                slab_count += 1
            elif parsed.get("构件类型") == "梁":
                beam_count += 1
        except ValidationError as e:
            errors.append({
                "行号": actual_line_no,
                "构件名": member_name,
                "错误": str(e)
            })

    project_info["构件列表"] = members

    total_data_rows = len(content_lines) - data_start_idx

    preview = {
        "总行数": total_data_rows,
        "识别构件数": len(members),
        "错误行数": len(errors),
        "楼板数": slab_count,
        "梁数": beam_count,
        "识别字段": sorted(field_to_idx.keys()),
        "未知表头": unknown_headers,
        "默认值继承": bool(default_dict),
    }

    return project_info, members, errors, warnings, preview
