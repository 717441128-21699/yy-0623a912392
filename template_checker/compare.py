from .calculator import calculate_member
from .materials import (
    get_steel_pipe_params, get_wood_joist_params, get_main_beam_params,
    get_materials
)
from .parser import parse_single_member, ValidationError


def _get_material(category, spec):
    """通用材料获取函数，失败返回None"""
    try:
        if category == "steel_pipe":
            return get_steel_pipe_params(spec)
        if category == "wood_joist":
            return get_wood_joist_params(spec)
        if category == "main_beam":
            return get_main_beam_params(spec)
    except Exception:
        return None
    return None


def estimate_material_usage(member_params):
    """估算构件材料用量，返回包含钢管重量(kg)、木方体积(m3)、扣件数量的字典"""
    usage = {
        "立杆钢管重量_kg": 0.0,
        "水平杆钢管重量_kg": 0.0,
        "钢管总重量_kg": 0.0,
        "次楞木方体积_m3": 0.0,
        "主楞材料体积_m3": 0.0,
        "木方总体积_m3": 0.0,
        "扣件数量": 0,
        "综合用量指数": 0.0,
    }

    try:
        if member_params["构件类型"] == "楼板":
            area_unit = 1.0
            span_length = member_params["立杆纵距"]
            span_width = member_params["立杆横距"]
            pole_count = max(1, int(round(area_unit / (span_length * span_width))))
        else:
            beam_width_m = member_params["梁宽"] / 1000.0
            span_length = member_params["立杆纵距"]
            pole_count = max(2, int(round(beam_width_m / span_length)) + 1)

        steel_spec = member_params["立杆钢管"]
        if isinstance(steel_spec, dict):
            pipe_mat = steel_spec
        else:
            pipe_mat = _get_material("steel_pipe", steel_spec)
        if pipe_mat:
            density = pipe_mat.get("density", 7850)
            area = pipe_mat.get("area", 0.000001)
            unit_weight_kgm = pipe_mat.get("weight_per_m")
            if not unit_weight_kgm:
                unit_weight_kgm = (density * area) / 1000.0
            if unit_weight_kgm <= 0 or unit_weight_kgm > 100:
                unit_weight_kgm = 3.84 if "3.0" in str(steel_spec) else 3.33
            support_h = member_params["支撑高度"]
            pole_pipe_len = support_h * pole_count

            step = member_params["步距"]
            step_count = max(1, int(support_h / step))
            if member_params["构件类型"] == "楼板":
                horiz_len_per_step = (span_length + span_width) * pole_count * 0.5
            else:
                horiz_len_per_step = span_length * pole_count * 1.5
            horiz_pipe_len = horiz_len_per_step * step_count

            total_pipe_m = pole_pipe_len + horiz_pipe_len
            usage["立杆钢管重量_kg"] = round(pole_pipe_len * unit_weight_kgm, 2)
            usage["水平杆钢管重量_kg"] = round(horiz_pipe_len * unit_weight_kgm, 2)
            usage["钢管总重量_kg"] = round(total_pipe_m * unit_weight_kgm, 2)
            usage["扣件数量"] = int(round(pole_count * step_count * 2.5))

        joist_spec = member_params["次楞木方"]
        if isinstance(joist_spec, dict):
            joist_mat = joist_spec
        else:
            joist_mat = _get_material("wood_joist", joist_spec)
        if joist_mat:
            jw = joist_mat.get("width", 50) / 1000.0
            jh = joist_mat.get("height", 80) / 1000.0
            jarea_m2 = jw * jh
            joist_spacing_m = member_params["次楞间距"] / 1000.0
            if member_params["构件类型"] == "楼板":
                joist_count_per_m2 = max(1, int(round(1.0 / joist_spacing_m)))
                joist_total_len = joist_count_per_m2 * span_width
            else:
                beam_w_m = member_params["梁宽"] / 1000.0
                joist_count = max(1, int(round(beam_w_m / joist_spacing_m)) + 1)
                joist_total_len = joist_count * span_length
            usage["次楞木方体积_m3"] = round(joist_total_len * jarea_m2, 6)

        main_type = member_params["主楞类型"]
        main_name = main_type.get("name") if isinstance(main_type, dict) else str(main_type)
        main_is_wood = isinstance(main_type, dict) and main_type.get("type") == "wood"
        if main_is_wood or (isinstance(main_name, str) and ("木" in main_name or main_name == "木方")):
            if isinstance(main_type, dict) and main_type.get("type") == "wood":
                main_mat = main_type
            else:
                main_mat = _get_material("wood_joist", main_type if isinstance(main_type, str) else main_name)
            if main_mat:
                mw = main_mat.get("width", 80) / 1000.0
                mh = main_mat.get("height", 80) / 1000.0
                marea = mw * mh
                main_spacing = member_params.get("主楞间距", member_params["立杆纵距"])
                if member_params["构件类型"] == "楼板":
                    main_count = max(1, int(round(1.0 / main_spacing)))
                    main_total_len = main_count * span_length
                else:
                    main_total_len = span_length * pole_count
                usage["主楞材料体积_m3"] = round(main_total_len * marea, 6)
            else:
                usage["主楞材料体积_m3"] = 0.0
        else:
            usage["主楞材料体积_m3"] = 0.0

        usage["木方总体积_m3"] = round(usage["次楞木方体积_m3"] + usage["主楞材料体积_m3"], 6)

        usage["综合用量指数"] = round(
            usage["钢管总重量_kg"] * 1.0 + usage["木方总体积_m3"] * 1500, 2
        )

    except Exception:
        pass

    return usage


def compare_schemes(base_member_params, schemes):
    """
    对同一构件进行多方案对比验算
    参数:
        base_member_params: dict, 基础构件参数（所有方案共用的部分）
        schemes: list of dict, 每个方案包含要覆盖的参数，如:
                 [{"方案名": "方案1", "支架布置": {"步距": "1.5m", ...}},
                  {"方案名": "方案2", "材料规格": {"主楞类型": "..."}}]
    返回: list of dict, 每个方案的结果
    """
    results = []
    for idx, scheme in enumerate(schemes):
        scheme_name = scheme.get("方案名", f"方案{idx + 1}")

        merged = _deep_merge_params(base_member_params, scheme)
        merged["构件名称"] = f"{base_member_params.get('构件名称', '构件')} [{scheme_name}]"

        try:
            normalized, _ = parse_single_member(merged)
            calc_result = calculate_member(normalized)
            usage = estimate_material_usage(normalized)
            passed = calc_result["全部满足"]
        except ValidationError as e:
            calc_result = {"全部满足": False, "_错误": str(e)}
            usage = estimate_material_usage(base_member_params)
            passed = False
        except Exception as e:
            calc_result = {"全部满足": False, "_错误": str(e)}
            usage = estimate_material_usage(base_member_params)
            passed = False

        results.append({
            "方案名": scheme_name,
            "是否通过": passed,
            "验算结果": calc_result,
            "材料用量": usage,
            "参数覆盖": scheme,
        })

    passed_schemes = [r for r in results if r["是否通过"]]
    if passed_schemes:
        passed_schemes.sort(key=lambda r: r["材料用量"]["综合用量指数"])
        recommended = passed_schemes[0]["方案名"]
    else:
        results.sort(key=lambda r: _max_ratio(r["验算结果"]))
        recommended = results[0]["方案名"] + " (最接近通过)"

    for r in results:
        r["是否推荐"] = (r["方案名"] == recommended)

    return results, recommended


def _deep_merge_params(base, override):
    """深拷贝 base，然后用 override 覆盖参数"""
    import copy
    merged = copy.deepcopy(base)

    if "支架布置" in override:
        if "支架布置" not in merged:
            merged["支架布置"] = {}
        merged["支架布置"].update(override["支架布置"])
    if "材料规格" in override:
        if "材料规格" not in merged:
            merged["材料规格"] = {}
        merged["材料规格"].update(override["材料规格"])
    for k in ("支撑高度", "混凝土厚度", "施工活荷载", "振捣荷载", "模板自重",
              "梁宽", "梁高", "模板类型", "模板厚度", "构件名称", "构件类型"):
        if k in override:
            merged[k] = override[k]
    if "方案名" in override and "构件名称" not in override:
        pass

    return merged


def _get_item_result(calc_result, item_key):
    """从计算结果中安全获取验算项目的CalculationResult对象"""
    if not calc_result:
        return None
    items = calc_result.get("各项结果", {})
    return items.get(item_key)


def _max_ratio(calc_result):
    """取各项验算比值中的最大值（用于方案排序，越小越好）"""
    if not calc_result or calc_result.get("全部满足"):
        return 999.0
    ratios = []
    for item_key in ("立杆承载力", "扣件抗滑", "次楞挠度", "主楞强度"):
        r = _get_item_result(calc_result, item_key)
        if r is not None and hasattr(r, "ratio") and r.ratio is not None:
            ratios.append(float(r.ratio))
    return max(ratios) if ratios else 999.0


def generate_compare_report(base_params, scheme_results, recommended):
    """生成多方案对比的文本报告"""
    lines = []
    w = 80
    lines.append("=" * w)
    lines.append("      模 板 支 撑 方 案 对 比 报 告".center(w - 10))
    lines.append("=" * w)
    lines.append(f"工程名称: {base_params.get('工程名称', '')}")
    lines.append(f"构件名称: {base_params.get('构件名称', '')}")
    lines.append(f"构件类型: {base_params.get('构件类型', '')}")

    loads = base_params.get("荷载参数", {})
    if base_params.get("构件类型") == "楼板":
        lines.append(f"混凝土厚度: {loads.get('混凝土厚度', '')}")
    else:
        lines.append(f"梁截面: {loads.get('梁宽', '')}x{loads.get('梁高', '')}")
    lines.append(f"支撑高度: {base_params.get('支撑高度', '')}")
    lines.append("-" * w)
    lines.append("")

    lines.append("【方案对比汇总表】")
    lines.append("-" * w)
    header = f"{'方案':<14} {'结果':<10} {'立杆比值':<10} {'抗滑比值':<10} {'挠度比值':<10} {'强度比值':<10} {'综合用量指数':<12}"
    lines.append(header)
    lines.append("-" * w)
    for r in scheme_results:
        cr = r["验算结果"]
        status = "[通过]" if r["是否通过"] else "[不通过]"
        rec = " [推荐]" if r["是否推荐"] else ""
        def _rv(key):
            obj = _get_item_result(cr, key)
            if obj is not None and hasattr(obj, "ratio") and obj.ratio is not None:
                return f"{obj.ratio:.3f}"
            return "   -"
        row = (f"{r['方案名']:<14} {status:<10} {_rv('立杆承载力'):<10} "
               f"{_rv('扣件抗滑'):<10} {_rv('次楞挠度'):<10} {_rv('主楞强度'):<10} "
               f"{r['材料用量']['综合用量指数']:<12.2f}{rec}")
        lines.append(row)
    lines.append("-" * w)
    lines.append("")

    lines.append("【材料用量明细】")
    lines.append("-" * w)
    header2 = f"{'方案':<12} {'钢管总重(kg)':<14} {'立杆(kg)':<12} {'水平杆(kg)':<14} {'木方总体积(m3)':<16} {'扣件数':<8}"
    lines.append(header2)
    lines.append("-" * w)
    for r in scheme_results:
        u = r["材料用量"]
        row = (f"{r['方案名']:<12} {u['钢管总重量_kg']:<14.2f} {u['立杆钢管重量_kg']:<12.2f} "
               f"{u['水平杆钢管重量_kg']:<14.4f} {u['木方总体积_m3']:<16.6f} {u['扣件数量']:<8}")
        lines.append(row)
    lines.append("-" * w)
    lines.append("")

    lines.append("【各方案参数差异】")
    for r in scheme_results:
        lines.append(f"  {r['方案名']}{' (推荐)' if r['是否推荐'] else ''}:")
        ov = r["参数覆盖"]
        for section in ("支架布置", "材料规格"):
            if section in ov:
                for k, v in ov[section].items():
                    lines.append(f"    - {section}.{k} = {v}")
        for k in ("步距", "立杆纵距", "立杆横距", "主楞类型"):
            if k in ov:
                lines.append(f"    - {k} = {ov[k]}")
        if r["是否通过"]:
            failed_items = []
        else:
            failed_items = _collect_failed(r["验算结果"])
            lines.append(f"    不满足项: {'; '.join(failed_items) if failed_items else '无'}")
        lines.append("")

    lines.append("【推荐方案结论】")
    lines.append(f"  推荐采用: {recommended}")
    passed_count = sum(1 for r in scheme_results if r["是否通过"])
    lines.append(f"  共 {len(scheme_results)} 组方案，其中 {passed_count} 组通过验算")
    if passed_count > 0:
        lines.append(f"  推荐理由: 在所有通过验算的方案中，综合用量指数最低，最省材料")
    else:
        lines.append(f"  注 意: 所有方案均不通过，推荐方案为最接近通过的一组，请进一步调整参数")
    lines.append("")
    lines.append("=" * w)
    return "\n".join(lines)


def _collect_failed(calc_result):
    failed = []
    for item_key in ("立杆承载力", "扣件抗滑", "次楞挠度", "主楞强度"):
        r = _get_item_result(calc_result, item_key)
        if r is not None and hasattr(r, "passed") and not r.passed:
            failed.append(item_key)
    return failed
