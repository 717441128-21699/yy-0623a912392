import re
import yaml
from .materials import (
    get_steel_pipe_params,
    get_wood_joist_params,
    get_main_beam_params,
    get_fastener_params,
)


REQUIRED_FIELDS_SINGLE = [
    "工程名称",
    "构件类型",
    "构件名称",
    "材料规格",
    "支架布置",
    "荷载参数",
    "支撑高度",
]

REQUIRED_FIELDS_BATCH = [
    "工程名称",
    "构件列表",
]

REQUIRED_MATERIAL_FIELDS = [
    "立杆钢管",
    "次楞木方",
    "主楞类型",
    "扣件类型",
]

REQUIRED_BRACKET_FIELDS = [
    "立杆纵距",
    "立杆横距",
    "步距",
    "次楞间距",
    "主楞间距",
]

REQUIRED_LOAD_FIELDS_SLAB = [
    "混凝土厚度",
    "施工活荷载",
]

REQUIRED_LOAD_FIELDS_BEAM = [
    "梁宽",
    "梁高",
    "施工活荷载",
]


class ValidationError(Exception):
    pass


def parse_value_with_unit(value_str, expected_units=None, target_unit=None):
    if value_str is None:
        return None

    if isinstance(value_str, (int, float)):
        return float(value_str)

    value_str = str(value_str).strip()

    if not value_str:
        return None

    pattern = r'^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(.*)$'
    match = re.match(pattern, value_str)

    if not match:
        raise ValidationError(f"无法解析数值: '{value_str}'")

    num = float(match.group(1))
    unit = match.group(2).strip()

    if expected_units and unit and unit not in expected_units:
        raise ValidationError(
            f"单位错误: '{unit}'，期望单位为 {', '.join(expected_units)}"
        )

    if target_unit == 'm' and unit in ('mm', '毫米'):
        num = num / 1000.0
        unit = 'm'
    elif target_unit == 'mm' and unit in ('m', '米'):
        num = num * 1000.0
        unit = 'mm'
    elif target_unit == 'm2' and unit in ('m²', '㎡'):
        unit = 'm2'
    elif target_unit and unit == '':
        unit = target_unit

    return num


def validate_range(value, min_val, max_val, field_name, unit=""):
    if value is None:
        return
    if value < min_val or value > max_val:
        raise ValidationError(
            f"{field_name} 数值异常: {value}{unit}，"
            f"合理范围为 {min_val}~{max_val}{unit}"
        )


def parse_and_validate_material(material_spec):
    errors = []
    warnings = []
    parsed = {}

    for field in REQUIRED_MATERIAL_FIELDS:
        if field not in material_spec:
            errors.append(f"材料规格缺少字段: {field}")

    if errors:
        raise ValidationError("; ".join(errors))

    steel_spec = material_spec.get("立杆钢管")
    steel_params = get_steel_pipe_params(steel_spec)
    if steel_params is None:
        from .materials import list_materials
        available = list_materials("steel_pipe")
        errors.append(
            f"立杆钢管规格 '{steel_spec}' 不在材料库中，"
            f"可用规格: {', '.join(available)}"
        )
    else:
        parsed["立杆钢管"] = steel_params
        parsed["立杆钢管规格"] = steel_spec

    wood_spec = material_spec.get("次楞木方")
    wood_params = get_wood_joist_params(wood_spec)
    if wood_params is None:
        from .materials import list_materials
        available = list_materials("wood_joist")
        errors.append(
            f"次楞木方规格 '{wood_spec}' 不在材料库中，"
            f"可用规格: {', '.join(available)}"
        )
    else:
        parsed["次楞木方"] = wood_params
        parsed["次楞木方规格"] = wood_spec

    beam_spec = material_spec.get("主楞类型")
    beam_params = get_main_beam_params(beam_spec)
    if beam_params is None:
        from .materials import list_materials
        available = list_materials("main_beam")
        errors.append(
            f"主楞类型 '{beam_spec}' 不在材料库中，"
            f"可用类型: {', '.join(available)}"
        )
    else:
        parsed["主楞"] = beam_params
        parsed["主楞类型"] = beam_spec

    fastener_spec = material_spec.get("扣件类型")
    fastener_params = get_fastener_params(fastener_spec)
    if fastener_params is None:
        from .materials import list_anti_slip_fasteners, list_materials
        available = list_materials("fastener")
        anti_slip = list_anti_slip_fasteners()
        errors.append(
            f"扣件类型 '{fastener_spec}' 不在材料库中，"
            f"可用类型: {', '.join(available)}；"
            f"其中可用于抗滑验算: {', '.join(anti_slip)}"
        )
    else:
        from .materials import is_fastener_suitable_for_anti_slip, list_anti_slip_fasteners
        suitable, remark = is_fastener_suitable_for_anti_slip(fastener_spec)
        if suitable is False:
            anti_slip = list_anti_slip_fasteners()
            errors.append(
                f"扣件类型 '{fastener_spec}' {remark}，"
                f"不适合用于模板支撑抗滑验算，"
                f"请改用: {', '.join(anti_slip)}"
            )
        else:
            parsed["扣件"] = fastener_params
            parsed["扣件类型"] = fastener_spec

    if errors:
        raise ValidationError("; ".join(errors))

    return parsed, warnings


def parse_and_validate_bracket(bracket_spec):
    errors = []
    warnings = []
    parsed = {}

    for field in REQUIRED_BRACKET_FIELDS:
        if field not in bracket_spec:
            errors.append(f"支架布置缺少字段: {field}")

    if errors:
        raise ValidationError("; ".join(errors))

    try:
        parsed["立杆纵距"] = parse_value_with_unit(
            bracket_spec["立杆纵距"],
            expected_units=["m", "mm", ""],
            target_unit="m"
        )
        validate_range(parsed["立杆纵距"], 0.3, 3.0, "立杆纵距", "m")
    except ValidationError as e:
        errors.append(str(e))

    try:
        parsed["立杆横距"] = parse_value_with_unit(
            bracket_spec["立杆横距"],
            expected_units=["m", "mm", ""],
            target_unit="m"
        )
        validate_range(parsed["立杆横距"], 0.3, 3.0, "立杆横距", "m")
    except ValidationError as e:
        errors.append(str(e))

    try:
        parsed["步距"] = parse_value_with_unit(
            bracket_spec["步距"],
            expected_units=["m", "mm", ""],
            target_unit="m"
        )
        validate_range(parsed["步距"], 0.6, 2.0, "步距", "m")
    except ValidationError as e:
        errors.append(str(e))

    try:
        parsed["次楞间距"] = parse_value_with_unit(
            bracket_spec["次楞间距"],
            expected_units=["mm", "m", ""],
            target_unit="mm"
        )
        validate_range(parsed["次楞间距"], 100, 600, "次楞间距", "mm")
    except ValidationError as e:
        errors.append(str(e))

    try:
        parsed["主楞间距"] = parse_value_with_unit(
            bracket_spec["主楞间距"],
            expected_units=["m", "mm", ""],
            target_unit="m"
        )
        validate_range(parsed["主楞间距"], 0.3, 3.0, "主楞间距", "m")
    except ValidationError as e:
        errors.append(str(e))

    if "扫地杆高度" in bracket_spec:
        try:
            parsed["扫地杆高度"] = parse_value_with_unit(
                bracket_spec["扫地杆高度"],
                expected_units=["mm", "m", ""],
                target_unit="mm"
            )
            if parsed["扫地杆高度"] > 300:
                warnings.append(
                    f"扫地杆高度 {parsed['扫地杆高度']}mm 偏高，"
                    f"建议不大于200mm"
                )
        except ValidationError as e:
            warnings.append(str(e))

    if errors:
        raise ValidationError("; ".join(errors))

    return parsed, warnings


def parse_and_validate_loads(load_spec, member_type):
    errors = []
    warnings = []
    parsed = {}

    if member_type == "楼板":
        required = REQUIRED_LOAD_FIELDS_SLAB
    elif member_type == "梁":
        required = REQUIRED_LOAD_FIELDS_BEAM
    else:
        errors.append(f"未知构件类型: {member_type}")
        raise ValidationError("; ".join(errors))

    for field in required:
        if field not in load_spec:
            errors.append(f"荷载参数缺少字段: {field}")

    if errors:
        raise ValidationError("; ".join(errors))

    if member_type == "楼板":
        try:
            parsed["混凝土厚度"] = parse_value_with_unit(
                load_spec["混凝土厚度"],
                expected_units=["mm", "m", ""],
                target_unit="mm"
            )
            validate_range(parsed["混凝土厚度"], 80, 500, "混凝土厚度", "mm")
        except ValidationError as e:
            errors.append(str(e))

    elif member_type == "梁":
        try:
            parsed["梁宽"] = parse_value_with_unit(
                load_spec["梁宽"],
                expected_units=["mm", "m", ""],
                target_unit="mm"
            )
            validate_range(parsed["梁宽"], 150, 1500, "梁宽", "mm")
        except ValidationError as e:
            errors.append(str(e))

        try:
            parsed["梁高"] = parse_value_with_unit(
                load_spec["梁高"],
                expected_units=["mm", "m", ""],
                target_unit="mm"
            )
            validate_range(parsed["梁高"], 300, 2500, "梁高", "mm")
        except ValidationError as e:
            errors.append(str(e))

    try:
        parsed["施工活荷载"] = parse_value_with_unit(
            load_spec["施工活荷载"],
            expected_units=["kN/m²", "kN/m2", "kn/m2", ""],
            target_unit="kN/m2"
        )
        validate_range(parsed["施工活荷载"], 1.0, 6.0, "施工活荷载", "kN/m²")
    except ValidationError as e:
        errors.append(str(e))

    if "振捣荷载" in load_spec:
        try:
            parsed["振捣荷载"] = parse_value_with_unit(
                load_spec["振捣荷载"],
                expected_units=["kN/m²", "kN/m2", "kn/m2", ""],
                target_unit="kN/m2"
            )
            validate_range(parsed["振捣荷载"], 1.0, 4.0, "振捣荷载", "kN/m²")
        except ValidationError as e:
            warnings.append(str(e))
    else:
        parsed["振捣荷载"] = 2.0

    if "模板自重" in load_spec:
        try:
            parsed["模板自重"] = parse_value_with_unit(
                load_spec["模板自重"],
                expected_units=["kN/m²", "kN/m2", "kn/m2", ""],
                target_unit="kN/m2"
            )
        except ValidationError as e:
            warnings.append(str(e))
    else:
        parsed["模板自重"] = 0.3

    if errors:
        raise ValidationError("; ".join(errors))

    return parsed, warnings


def parse_single_member(data):
    errors = []
    warnings = []
    parsed = {}

    for field in REQUIRED_FIELDS_SINGLE:
        if field not in data:
            errors.append(f"缺少必填字段: {field}")

    if errors:
        raise ValidationError("; ".join(errors))

    parsed["工程名称"] = data.get("工程名称")
    parsed["构件类型"] = data.get("构件类型")
    parsed["构件名称"] = data.get("构件名称")
    parsed["计算人"] = data.get("计算人", "")
    parsed["计算日期"] = data.get("计算日期", "")

    if parsed["构件类型"] not in ("楼板", "梁"):
        errors.append(f"构件类型 '{parsed['构件类型']}' 不支持，仅支持 楼板 或 梁")
        raise ValidationError("; ".join(errors))

    if "模板类型" in data:
        parsed["模板类型"] = data["模板类型"]
    else:
        warnings.append("未指定模板类型，默认按胶合板计算")
        parsed["模板类型"] = "胶合板"

    if "模板厚度" in data:
        try:
            parsed["模板厚度"] = parse_value_with_unit(
                data["模板厚度"],
                expected_units=["mm", ""],
                target_unit="mm"
            )
        except ValidationError as e:
            warnings.append(str(e))
            parsed["模板厚度"] = 15.0
    else:
        parsed["模板厚度"] = 15.0

    material_data = data.get("材料规格", {})
    try:
        material_parsed, mat_warnings = parse_and_validate_material(material_data)
        parsed.update(material_parsed)
        warnings.extend(mat_warnings)
    except ValidationError as e:
        errors.append(str(e))

    bracket_data = data.get("支架布置", {})
    try:
        bracket_parsed, bracket_warnings = parse_and_validate_bracket(bracket_data)
        parsed.update(bracket_parsed)
        warnings.extend(bracket_warnings)
    except ValidationError as e:
        errors.append(str(e))

    load_data = data.get("荷载参数", {})
    try:
        load_parsed, load_warnings = parse_and_validate_loads(
            load_data, parsed["构件类型"]
        )
        parsed.update(load_parsed)
        warnings.extend(load_warnings)
    except ValidationError as e:
        errors.append(str(e))

    try:
        parsed["支撑高度"] = parse_value_with_unit(
            data["支撑高度"],
            expected_units=["m", "mm", ""],
            target_unit="m"
        )
        validate_range(parsed["支撑高度"], 1.5, 20.0, "支撑高度", "m")
        if parsed["支撑高度"] > 8.0:
            warnings.append(
                f"支撑高度 {parsed['支撑高度']}m 大于8m，"
                f"属于高支模，需进行专项论证"
            )
    except ValidationError as e:
        errors.append(str(e))

    if "验算项目" in data:
        parsed["验算项目"] = data["验算项目"]
    else:
        parsed["验算项目"] = [
            "立杆承载力",
            "扣件抗滑",
            "次楞挠度",
            "主楞强度",
        ]

    if errors:
        raise ValidationError("; ".join(errors))

    return parsed, warnings


def parse_batch_file(data):
    errors = []
    warnings = []
    parsed = {
        "工程名称": data.get("工程名称", ""),
        "计算人": data.get("计算人", ""),
        "计算日期": data.get("计算日期", ""),
        "构件列表": [],
        "验算项目": data.get("验算项目", [
            "立杆承载力",
            "扣件抗滑",
            "次楞挠度",
            "主楞强度",
        ]),
    }

    for field in REQUIRED_FIELDS_BATCH:
        if field not in data:
            errors.append(f"缺少必填字段: {field}")

    if errors:
        raise ValidationError("; ".join(errors))

    default_params = data.get("默认参数", {})
    members = data.get("构件列表", [])

    if not members:
        errors.append("构件列表为空，请至少添加一个构件")
        raise ValidationError("; ".join(errors))

    for idx, member in enumerate(members, 1):
        member_name = member.get("构件名称", f"构件{idx}")

        merged_member = _merge_default_params(member, default_params)

        try:
            member_parsed, member_warnings = parse_single_member(
                {**merged_member, "工程名称": parsed["工程名称"]}
            )
            parsed["构件列表"].append(member_parsed)
            for w in member_warnings:
                warnings.append(f"[{member_name}] {w}")
        except ValidationError as e:
            errors.append(f"[{member_name}] {str(e)}")

    if errors:
        raise ValidationError("; ".join(errors))

    return parsed, warnings


def _merge_default_params(member, defaults):
    merged = dict(defaults) if defaults else {}

    for key, value in member.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    if "荷载参数" not in merged:
        merged["荷载参数"] = {}

    load_keys = ["混凝土厚度", "施工活荷载", "振捣荷载", "模板自重", "梁宽", "梁高"]
    for key in load_keys:
        if key in merged and key not in merged["荷载参数"]:
            merged["荷载参数"][key] = merged[key]

    return merged


def parse_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValidationError(f"YAML文件解析错误: {e}")
    except FileNotFoundError:
        raise ValidationError(f"文件不存在: {filepath}")

    if not isinstance(data, dict):
        raise ValidationError("参数文件格式错误，根节点应为字典")

    if "构件列表" in data:
        result, warnings = parse_batch_file(data)
        result["模式"] = "batch"
    else:
        result, warnings = parse_single_member(data)
        result["模式"] = "single"

    return result, warnings
