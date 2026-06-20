import os
import json
import copy


DEFAULT_MATERIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "materials_default.json"
)

CUSTOM_MATERIALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "materials_custom.json"
)

_MATERIAL_PARAMS = None
_MATERIAL_SOURCE = "default"


def _load_materials_from_file(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "_meta" in data:
            data.pop("_meta")
        return data
    except (json.JSONDecodeError, IOError):
        return None


def _load_default_materials():
    return _load_materials_from_file(DEFAULT_MATERIALS_PATH) or {
        "steel_pipe": {
            "φ48×3.0": {
                "outer_diameter": 48.0, "thickness": 3.0, "inner_diameter": 42.0,
                "area": 4.24, "modulus": 206000.0, "f_y": 205.0, "f_v": 120.0,
                "weight_per_m": 3.33,
            },
            "φ48×3.5": {
                "outer_diameter": 48.0, "thickness": 3.5, "inner_diameter": 41.0,
                "area": 4.89, "modulus": 206000.0, "f_y": 205.0, "f_v": 120.0,
                "weight_per_m": 3.84,
            },
        },
        "wood_joist": {
            "50×80": {
                "width": 50.0, "height": 80.0, "area": 4000.0,
                "modulus": 9000.0, "f_m": 13.0, "f_v": 1.4,
                "deflection_limit_ratio": 250,
            },
            "50×100": {
                "width": 50.0, "height": 100.0, "area": 5000.0,
                "modulus": 9000.0, "f_m": 13.0, "f_v": 1.4,
                "deflection_limit_ratio": 250,
            },
        },
        "main_beam": {
            "φ48×3.0双钢管": {
                "type": "double_steel", "spec": "φ48×3.0", "count": 2,
                "area": 8.48, "modulus": 206000.0, "f_m": 205.0, "f_v": 120.0,
            },
            "10#槽钢": {
                "type": "channel", "area": 12.74, "modulus": 206000.0,
                "f_m": 215.0, "f_v": 125.0, "W_x": 39.7, "I_x": 198.0,
            },
        },
        "fastener": {
            "直角扣件": {"anti_slip_capacity": 8.0, "tensile_capacity": 0.0, "for_anti_slip": True},
            "旋转扣件": {"anti_slip_capacity": 8.0, "tensile_capacity": 0.0, "for_anti_slip": True},
            "对接扣件": {"anti_slip_capacity": 0.0, "tensile_capacity": 6.0, "for_anti_slip": False},
        },
        "concrete": {"density": 24.0},
        "template": {
            "plywood_15mm": {"thickness": 15.0, "weight_per_m2": 0.9},
            "plywood_18mm": {"thickness": 18.0, "weight_per_m2": 1.08},
        },
        "live_load": {
            "construction_standard": {"value": 2.0},
            "construction_heavy": {"value": 2.5},
            "pouring_standard": {"value": 2.0},
            "pouring_heavy": {"value": 4.0},
        },
    }


def _ensure_materials_loaded():
    global _MATERIAL_PARAMS, _MATERIAL_SOURCE
    if _MATERIAL_PARAMS is None:
        custom = _load_materials_from_file(CUSTOM_MATERIALS_PATH)
        if custom:
            _MATERIAL_PARAMS = custom
            _MATERIAL_SOURCE = f"custom: {CUSTOM_MATERIALS_PATH}"
        else:
            _MATERIAL_PARAMS = _load_default_materials()
            _MATERIAL_SOURCE = f"default: {DEFAULT_MATERIALS_PATH}"


def reload_materials():
    global _MATERIAL_PARAMS, _MATERIAL_SOURCE
    _MATERIAL_PARAMS = None
    _MATERIAL_SOURCE = "default"
    try:
        if os.path.exists(CUSTOM_MATERIALS_PATH):
            os.remove(CUSTOM_MATERIALS_PATH)
    except IOError:
        pass
    _ensure_materials_loaded()
    return _MATERIAL_SOURCE


def load_custom_materials(filepath):
    global _MATERIAL_PARAMS, _MATERIAL_SOURCE
    custom = _load_materials_from_file(filepath)
    if custom is None:
        return False, f"无法加载材料库文件: {filepath}"

    errors = validate_materials_data(custom)
    if errors:
        return False, "材料库校验失败:\n  - " + "\n  - ".join(errors)

    try:
        import shutil
        os.makedirs(os.path.dirname(CUSTOM_MATERIALS_PATH), exist_ok=True)
        shutil.copyfile(filepath, CUSTOM_MATERIALS_PATH)
    except IOError as e:
        return False, f"无法持久化材料库到 {CUSTOM_MATERIALS_PATH}: {e}"

    _MATERIAL_PARAMS = custom
    _MATERIAL_SOURCE = f"custom: {CUSTOM_MATERIALS_PATH}"
    return True, f"已加载自定义材料库: {CUSTOM_MATERIALS_PATH} (从 {filepath} 导入)"


def _is_positive_number(value, field_name, errors, prefix):
    if not isinstance(value, (int, float)):
        errors.append(f"{prefix}字段[{field_name}]必须是数字，当前值: {value}")
        return False
    if value <= 0:
        errors.append(f"{prefix}字段[{field_name}]必须为正数，当前值: {value}")
        return False
    return True


def validate_materials_data(data):
    errors = []
    warnings = []

    required_categories = ["steel_pipe", "wood_joist", "main_beam", "fastener"]
    for cat in required_categories:
        if cat not in data:
            errors.append(f"缺少材料类别: {cat}")
        elif not isinstance(data[cat], dict) or len(data[cat]) == 0:
            errors.append(f"材料类别[{cat}]为空或不是字典")

    if "steel_pipe" in data and isinstance(data["steel_pipe"], dict):
        for name, spec in data["steel_pipe"].items():
            prefix = f"钢管[{name}]"
            if not isinstance(spec, dict):
                errors.append(f"{prefix}不是字典格式")
                continue
            required_fields = ["outer_diameter", "thickness", "inner_diameter",
                               "area", "modulus", "f_y", "f_v"]
            for field in required_fields:
                if field not in spec:
                    errors.append(f"{prefix}缺少必填字段: {field}")
                else:
                    _is_positive_number(spec[field], field, errors, prefix)
            if "outer_diameter" in spec and "inner_diameter" in spec:
                if isinstance(spec["outer_diameter"], (int, float)) and isinstance(spec["inner_diameter"], (int, float)):
                    if spec["inner_diameter"] >= spec["outer_diameter"]:
                        errors.append(f"{prefix}内径({spec['inner_diameter']})必须小于外径({spec['outer_diameter']})")
            if "outer_diameter" in spec and "thickness" in spec:
                if isinstance(spec["outer_diameter"], (int, float)) and isinstance(spec["thickness"], (int, float)):
                    expected_inner = round(spec["outer_diameter"] - 2 * spec["thickness"], 2)
                    if "inner_diameter" in spec and isinstance(spec["inner_diameter"], (int, float)):
                        if abs(spec["inner_diameter"] - expected_inner) > 1.0:
                            warnings.append(f"{prefix}内径({spec['inner_diameter']})与外径壁厚推算值({expected_inner})偏差超过1mm")

    if "wood_joist" in data and isinstance(data["wood_joist"], dict):
        for name, spec in data["wood_joist"].items():
            prefix = f"木方[{name}]"
            if not isinstance(spec, dict):
                errors.append(f"{prefix}不是字典格式")
                continue
            required_fields = ["width", "height", "area", "modulus", "f_m", "f_v", "deflection_limit_ratio"]
            for field in required_fields:
                if field not in spec:
                    errors.append(f"{prefix}缺少必填字段: {field}")
                else:
                    _is_positive_number(spec[field], field, errors, prefix)
            if "width" in spec and "height" in spec and "area" in spec:
                if all(isinstance(spec[f], (int, float)) for f in ["width", "height", "area"]):
                    expected_area = spec["width"] * spec["height"]
                    if abs(spec["area"] - expected_area) / expected_area > 0.1:
                        warnings.append(f"{prefix}截面积({spec['area']})与宽高乘积({expected_area})偏差超过10%")

    if "main_beam" in data and isinstance(data["main_beam"], dict):
        steel_pipes = data.get("steel_pipe", {}) if isinstance(data.get("steel_pipe"), dict) else {}
        for name, spec in data["main_beam"].items():
            prefix = f"主楞[{name}]"
            if not isinstance(spec, dict):
                errors.append(f"{prefix}不是字典格式")
                continue
            if "type" not in spec:
                errors.append(f"{prefix}缺少必填字段: type (双钢管=double_steel, 槽钢=channel, 木方=wood)")
                continue
            beam_type = spec["type"]
            if beam_type == "double_steel":
                required_fields = ["spec", "count", "area", "modulus", "f_m", "f_v"]
                for field in required_fields:
                    if field not in spec:
                        errors.append(f"{prefix}(双钢管)缺少必填字段: {field}")
                    elif field == "spec":
                        if not isinstance(spec["spec"], str) or not spec["spec"]:
                            errors.append(f"{prefix}(双钢管)字段[spec]必须是非空字符串")
                        elif spec["spec"] not in steel_pipes:
                            errors.append(f"{prefix}(双钢管)引用的钢管规格[{spec['spec']}]在steel_pipe类别中不存在")
                    elif field == "count":
                        if not isinstance(spec["count"], int) or spec["count"] < 1:
                            errors.append(f"{prefix}(双钢管)字段[count]必须是正整数，当前值: {spec['count']}")
                    else:
                        _is_positive_number(spec[field], field, errors, prefix + "(双钢管)")
            elif beam_type == "channel":
                required_fields = ["area", "modulus", "f_m", "f_v", "W_x", "I_x"]
                for field in required_fields:
                    if field not in spec:
                        errors.append(f"{prefix}(槽钢)缺少必填字段: {field}")
                    else:
                        _is_positive_number(spec[field], field, errors, prefix + "(槽钢)")
            elif beam_type == "wood":
                required_fields = ["width", "height", "area", "modulus", "f_m", "f_v"]
                for field in required_fields:
                    if field not in spec:
                        errors.append(f"{prefix}(木方)缺少必填字段: {field}")
                    else:
                        _is_positive_number(spec[field], field, errors, prefix + "(木方)")
                if "width" in spec and "height" in spec and "area" in spec:
                    if all(isinstance(spec[f], (int, float)) for f in ["width", "height", "area"]):
                        expected_area = spec["width"] * spec["height"]
                        if abs(spec["area"] - expected_area) / expected_area > 0.1:
                            warnings.append(f"{prefix}(木方)截面积({spec['area']})与宽高乘积({expected_area})偏差超过10%")
            else:
                errors.append(f"{prefix}未知类型: {beam_type}，可选值: double_steel, channel, wood")

    if "fastener" in data and isinstance(data["fastener"], dict):
        for name, spec in data["fastener"].items():
            prefix = f"扣件[{name}]"
            if not isinstance(spec, dict):
                errors.append(f"{prefix}不是字典格式")
                continue
            if "for_anti_slip" not in spec:
                errors.append(f"{prefix}缺少必填字段: for_anti_slip (布尔值，是否可用于抗滑验算)")
            elif not isinstance(spec["for_anti_slip"], bool):
                errors.append(f"{prefix}字段[for_anti_slip]必须是布尔值true/false")

            if "anti_slip_capacity" not in spec:
                errors.append(f"{prefix}缺少必填字段: anti_slip_capacity (抗滑承载力 kN)")
            else:
                if not isinstance(spec["anti_slip_capacity"], (int, float)):
                    errors.append(f"{prefix}字段[anti_slip_capacity]必须是数字，当前值: {spec['anti_slip_capacity']}")
                elif spec["anti_slip_capacity"] < 0:
                    errors.append(f"{prefix}字段[anti_slip_capacity]不能为负数，当前值: {spec['anti_slip_capacity']}")
                elif spec.get("for_anti_slip") is True and spec["anti_slip_capacity"] <= 0:
                    errors.append(f"{prefix}标记为可抗滑(for_anti_slip=true)但抗滑承载力为0或负数，必须设置正数抗滑承载力")

            if "tensile_capacity" not in spec:
                errors.append(f"{prefix}缺少必填字段: tensile_capacity (抗拉承载力 kN，对接扣件需设正数)")
            elif not isinstance(spec["tensile_capacity"], (int, float)) or spec["tensile_capacity"] < 0:
                errors.append(f"{prefix}字段[tensile_capacity]必须是非负数字")

            if spec.get("for_anti_slip") is False and spec.get("tensile_capacity", 0) <= 0:
                warnings.append(f"{prefix}不可用于抗滑且抗拉承载力为0，仅标记型扣件")

    if "concrete" in data:
        if not isinstance(data["concrete"], dict):
            errors.append("类别[concrete]不是字典格式")
        elif "density" not in data["concrete"]:
            errors.append("类别[concrete]缺少字段: density (重度 kN/m3)")
        else:
            _is_positive_number(data["concrete"]["density"], "density", errors, "concrete")

    return errors


def get_materials_source():
    _ensure_materials_loaded()
    return _MATERIAL_SOURCE


def get_materials():
    _ensure_materials_loaded()
    return copy.deepcopy(_MATERIAL_PARAMS)


def get_steel_pipe_params(spec):
    _ensure_materials_loaded()
    if spec in _MATERIAL_PARAMS.get("steel_pipe", {}):
        return copy.deepcopy(_MATERIAL_PARAMS["steel_pipe"][spec])
    return None


def get_wood_joist_params(spec):
    _ensure_materials_loaded()
    if spec in _MATERIAL_PARAMS.get("wood_joist", {}):
        return copy.deepcopy(_MATERIAL_PARAMS["wood_joist"][spec])
    return None


def get_main_beam_params(spec):
    _ensure_materials_loaded()
    if spec in _MATERIAL_PARAMS.get("main_beam", {}):
        return copy.deepcopy(_MATERIAL_PARAMS["main_beam"][spec])
    return None


def get_fastener_params(spec):
    _ensure_materials_loaded()
    if spec in _MATERIAL_PARAMS.get("fastener", {}):
        return copy.deepcopy(_MATERIAL_PARAMS["fastener"][spec])
    return None


def is_fastener_suitable_for_anti_slip(spec):
    params = get_fastener_params(spec)
    if params is None:
        return None, "扣件规格不存在"
    suitable = params.get("for_anti_slip", False)
    remark = params.get("remark", "")
    if suitable:
        return True, remark
    else:
        return False, remark or "该扣件不适用抗滑验算"


def list_anti_slip_fasteners():
    _ensure_materials_loaded()
    result = []
    for name, spec in _MATERIAL_PARAMS.get("fastener", {}).items():
        if spec.get("for_anti_slip", False):
            result.append(name)
    return result


def list_materials(category=None, detail=False):
    _ensure_materials_loaded()
    if category:
        if category in _MATERIAL_PARAMS:
            if detail:
                return {k: v for k, v in _MATERIAL_PARAMS[category].items()}
            return list(_MATERIAL_PARAMS[category].keys())
        return []
    if detail:
        return copy.deepcopy(_MATERIAL_PARAMS)
    return {k: list(v.keys()) for k, v in _MATERIAL_PARAMS.items()}


def export_default_materials(output_path):
    default = _load_default_materials()
    default_with_meta = {
        "_meta": {
            "version": "1.0.0",
            "description": "模板支撑验算工具 - 材料规格库（可在此基础上自定义）",
            "updated": "2026-06-21"
        }
    }
    default_with_meta.update(default)

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(default_with_meta, f, ensure_ascii=False, indent=2)
    return output_path
