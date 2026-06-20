import os
from datetime import datetime


def format_single_result(member_result, warnings=None):
    lines = []
    lines.append("=" * 70)
    lines.append("          模 板 支 撑 验 算 报 告")
    lines.append("=" * 70)

    params = member_result["参数"]
    lines.append(f"工程名称: {params.get('工程名称', '')}")
    lines.append(f"构件名称: {params.get('构件名称', '')}")
    lines.append(f"构件类型: {params.get('构件类型', '')}")
    if params.get("计算人"):
        lines.append(f"计算人:   {params.get('计算人', '')}")
    if params.get("计算日期"):
        lines.append(f"计算日期: {params.get('计算日期', '')}")
    lines.append("-" * 70)

    lines.append("")
    lines.append("【基本参数】")
    lines.append(f"  支撑高度: {params.get('支撑高度', 0):.2f} m")

    if params["构件类型"] == "楼板":
        lines.append(f"  混凝土厚度: {params.get('混凝土厚度', 0):.0f} mm")
    else:
        lines.append(
            f"  梁截面: {params.get('梁宽', 0):.0f} × {params.get('梁高', 0):.0f} mm"
        )

    lines.append(
        f"  立杆纵距 × 横距: "
        f"{params.get('立杆纵距', 0):.2f}m × {params.get('立杆横距', 0):.2f}m"
    )
    lines.append(f"  步距: {params.get('步距', 0):.2f} m")
    lines.append(f"  次楞间距: {params.get('次楞间距', 0):.0f} mm")
    lines.append(f"  主楞间距: {params.get('主楞间距', 0):.2f} m")
    lines.append(f"  立杆钢管: {params.get('立杆钢管规格', '')}")
    lines.append(f"  次楞木方: {params.get('次楞木方规格', '')}")
    lines.append(f"  主楞类型: {params.get('主楞类型', '')}")
    lines.append(f"  扣件类型: {params.get('扣件类型', '')}")
    lines.append(f"  施工活荷载: {params.get('施工活荷载', 0):.1f} kN/m²")

    lines.append("")
    lines.append("-" * 70)
    lines.append("【验算结果汇总】")
    lines.append("-" * 70)

    all_passed = member_result["全部满足"]
    status_str = "全部满足" if all_passed else "存在不满足项"
    lines.append(f"  总体结论: {status_str}")
    lines.append("")

    for name, result in member_result["各项结果"].items():
        status = "[OK] 满足" if result.passed else "[FAIL] 不满足"
        lines.append(f"  {name}: {status}  (比值: {result.ratio:.3f})")

    lines.append("")
    lines.append("=" * 70)
    lines.append("【详细验算过程】")
    lines.append("=" * 70)

    for name, result in member_result["各项结果"].items():
        lines.append("")
        lines.append(f"--- {name} ---")
        lines.append(f"  结论: {'满足要求' if result.passed else '不满足要求'}")
        lines.append(f"  计算值: {result.calculated_value}")
        lines.append(f"  限值:   {result.limit_value}")
        lines.append(f"  比值:   {result.ratio:.3f}")
        lines.append("")
        lines.append("  计算过程:")
        for key, value in result.details.items():
            lines.append(f"    {key}: {value}")
        lines.append("")
        lines.append("  建议:")
        for idx, sug in enumerate(result.suggestions, 1):
            lines.append(f"    {idx}. {sug}")

    if warnings:
        lines.append("")
        lines.append("=" * 70)
        lines.append("【警告信息】")
        lines.append("=" * 70)
        for w in warnings:
            lines.append(f"  [!] {w}")

    lines.append("")
    lines.append("=" * 70)
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    return "\n".join(lines)


def format_batch_result(batch_data, member_results, warnings=None):
    lines = []
    lines.append("=" * 70)
    lines.append("      模 板 支 撑 批 量 验 算 报 告")
    lines.append("=" * 70)

    lines.append(f"工程名称: {batch_data.get('工程名称', '')}")
    if batch_data.get("计算人"):
        lines.append(f"计算人:   {batch_data.get('计算人', '')}")
    if batch_data.get("计算日期"):
        lines.append(f"计算日期: {batch_data.get('计算日期', '')}")
    lines.append(f"构件数量: {len(member_results)} 个")
    lines.append("-" * 70)

    lines.append("")
    lines.append("【验算结果汇总表】")
    lines.append("-" * 70)

    header = f"{'序号':<4}{'构件名称':<25}{'类型':<6}"
    check_items = list(member_results[0]["各项结果"].keys()) if member_results else []
    for item in check_items:
        header += f"{item[:4]:<8}"
    header += " 结论"
    lines.append(header)
    lines.append("-" * 70)

    passed_count = 0
    for idx, result in enumerate(member_results, 1):
        row = f"{idx:<4}{result['构件名称'][:24]:<25}{result['构件类型']:<6}"
        for item in check_items:
            r = result["各项结果"][item]
            status = "OK" if r.passed else "FAIL"
            row += f"{status:<8}"
        overall = "通过" if result["全部满足"] else "不通过"
        row += f" {overall}"
        lines.append(row)
        if result["全部满足"]:
            passed_count += 1

    lines.append("-" * 70)
    lines.append(
        f"汇总: {passed_count}/{len(member_results)} 个构件全部满足要求"
    )

    failed_members = [r for r in member_results if not r["全部满足"]]
    if failed_members:
        lines.append("")
        lines.append("=" * 70)
        lines.append("【不满足项详情及建议】")
        lines.append("=" * 70)

        for result in failed_members:
            lines.append("")
            lines.append(f"* {result['构件名称']} ({result['构件类型']})")
            for name, check_result in result["各项结果"].items():
                if not check_result.passed:
                    lines.append(f"  > {name}: 不满足 (比值: {check_result.ratio:.3f})")
                    for sug in check_result.suggestions:
                        lines.append(f"     建议: {sug}")

    lines.append("")
    lines.append("=" * 70)
    lines.append("【各构件验算概要】")
    lines.append("=" * 70)

    for idx, result in enumerate(member_results, 1):
        lines.append("")
        lines.append(f"--- [{idx}] {result['构件名称']} ---")
        params = result["参数"]
        if params["构件类型"] == "楼板":
            lines.append(
                f"  板厚{params.get('混凝土厚度', 0):.0f}mm, "
                f"立杆{params.get('立杆纵距', 0):.2f}×"
                f"{params.get('立杆横距', 0):.2f}m, "
                f"步距{params.get('步距', 0):.2f}m, "
                f"高{params.get('支撑高度', 0):.2f}m"
            )
        else:
            lines.append(
                f"  梁{params.get('梁宽', 0):.0f}×{params.get('梁高', 0):.0f}mm, "
                f"立杆{params.get('立杆纵距', 0):.2f}×"
                f"{params.get('立杆横距', 0):.2f}m, "
                f"步距{params.get('步距', 0):.2f}m, "
                f"高{params.get('支撑高度', 0):.2f}m"
            )

        for name, check_result in result["各项结果"].items():
            status = "满足" if check_result.passed else "不满足"
            lines.append(
                f"  {name}: {status} "
                f"(计算值={check_result.calculated_value}, "
                f"限值={check_result.limit_value}, "
                f"比值={check_result.ratio:.3f})"
            )

    if warnings:
        lines.append("")
        lines.append("=" * 70)
        lines.append("【警告信息】")
        lines.append("=" * 70)
        for w in warnings:
            lines.append(f"  [!] {w}")

    lines.append("")
    lines.append("=" * 70)
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_report(content, output_path):
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def generate_output(parsed_data, results, warnings=None, output_path=None):
    if parsed_data["模式"] == "single":
        content = format_single_result(results, warnings)
    else:
        content = format_batch_result(parsed_data, results, warnings)

    if output_path:
        save_report(content, output_path)

    return content
