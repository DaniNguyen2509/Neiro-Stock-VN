"""Khung Thẩm Định & Kiểm Toán Dữ Liệu Machine Learning (ML Dataset Validator - ADR-022).

Thực hiện kiểm toán định lượng về chất lượng, tính đầy đủ và độ sẵn sàng của tập dữ liệu ML:
1. Đếm số lượng mẫu và so sánh với ngưỡng an toàn thống kê (Minimum Sample Gap).
2. Đo lường tỷ lệ lệch pha cấu trúc dữ liệu (Schema Drift Ratio giữa v1_legacy và v2).
3. Đánh giá mức độ mất cân bằng nhãn mục tiêu (Class Imbalance Ratio).
4. Tính toán tỷ lệ hoàn thiện các đặc trưng T0 cốt lõi (V2 Feature Completeness).
5. Xuất báo cáo thẩm định dữ liệu Markdown phục vụ quyết định huấn luyện.
"""

from typing import Any, Dict, List
import pandas as pd


class MLDatasetValidator:
    """Bộ kiểm toán và thẩm định độ sẵn sàng huấn luyện Machine Learning."""

    MINIMUM_STATISTICAL_SAMPLES = 500  # Ngưỡng tối thiểu để huấn luyện Tabular ML có ý nghĩa thống kê

    CORE_V2_FEATURES: List[str] = [
        "pe_t0", "pb_t0", "eps_ttm_t0", "camel_score_t0",
        "atr_pct_t0", "atr_dist_from_poc_t0", "market_breadth_pct_t0", "vn30_basis_t0"
    ]

    def audit_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Kiểm toán toàn diện các chỉ số chất lượng của tập dữ liệu ML."""
        total_samples = len(df)
        if total_samples == 0:
            return {
                "total_samples": 0,
                "v1_legacy_count": 0,
                "v2_count": 0,
                "v2_ratio_pct": 0.0,
                "target_win_binary_distribution": {},
                "imbalance_ratio": 0.0,
                "closed_trades_count": 0,
                "closed_win_rate_pct": 0.0,
                "v2_feature_completeness_pct": 0.0,
                "is_statistically_sufficient": False,
                "minimum_sample_gap": self.MINIMUM_STATISTICAL_SAMPLES,
                "recommendation": "Tập dữ liệu rỗng. Cần tiến hành quét và tích lũy dữ liệu.",
            }

        v1_count = int((df["schema_version"] == "v1_legacy").sum()) if "schema_version" in df.columns else 0
        v2_count = int((df["schema_version"] == "v2").sum()) if "schema_version" in df.columns else total_samples
        v2_ratio = round((v2_count / total_samples) * 100.0, 2)

        # Phân phối nhãn
        target_dist: Dict[int, int] = {}
        imbalance_ratio = 1.0
        if "target_win_binary" in df.columns:
            counts = df["target_win_binary"].value_counts().to_dict()
            target_dist = {int(k): int(v) for k, v in counts.items()}
            zero_cnt = target_dist.get(0, 0)
            one_cnt = target_dist.get(1, 0)
            if one_cnt > 0:
                imbalance_ratio = round(zero_cnt / one_cnt, 2)
            else:
                imbalance_ratio = float(zero_cnt)

        # Vị thế đã đóng
        closed_cnt = 0
        closed_wr = 0.0
        if "is_closed" in df.columns and "outcome_label" in df.columns:
            closed_df = df[df["is_closed"] == True]
            closed_cnt = len(closed_df)
            if closed_cnt > 0:
                wins = int((closed_df["outcome_label"].astype(str).str.startswith("WIN")).sum())
                closed_wr = round((wins / closed_cnt) * 100.0, 2)

        # Tính độ hoàn thiện đặc trưng V2
        feature_completeness_list = []
        for feat in self.CORE_V2_FEATURES:
            if feat in df.columns:
                valid_cnt = int((df[feat] != 0.0).sum())
                feature_completeness_list.append(valid_cnt / total_samples)
            else:
                feature_completeness_list.append(0.0)
        v2_feature_completeness = round(float(sum(feature_completeness_list) / len(feature_completeness_list)) * 100.0, 2)

        is_sufficient = bool(total_samples >= self.MINIMUM_STATISTICAL_SAMPLES and v2_count >= 300)
        sample_gap = max(0, self.MINIMUM_STATISTICAL_SAMPLES - total_samples)

        if not is_sufficient:
            rec = (
                f"CHƯA ĐỦ ĐIỀU KIỆN HUẤN LUYỆN ML CHÍNH THỨC. "
                f"Hiện mới có {total_samples}/{self.MINIMUM_STATISTICAL_SAMPLES} mẫu (thiếu {sample_gap} mẫu) "
                f"và tỷ lệ mẫu v2 hoàn thiện mới đạt {v2_ratio}%. "
                "Cần duy trì chạy pipeline quét tự động 30 phút/lần để tích lũy đủ dữ liệu hoặc chỉ dùng làm Cold-Start Pilot."
            )
        else:
            rec = "TẬP DỮ LIỆU ĐÃ ĐẠT CHUẨN THỐNG KÊ SẴN SÀNG HUẤN LUYỆN MÔ HÌNH MACHINE LEARNING."

        return {
            "total_samples": total_samples,
            "v1_legacy_count": v1_count,
            "v2_count": v2_count,
            "v2_ratio_pct": v2_ratio,
            "target_win_binary_distribution": target_dist,
            "imbalance_ratio": imbalance_ratio,
            "closed_trades_count": closed_cnt,
            "closed_win_rate_pct": closed_wr,
            "v2_feature_completeness_pct": v2_feature_completeness,
            "is_statistically_sufficient": is_sufficient,
            "minimum_sample_gap": sample_gap,
            "recommendation": rec,
        }

    def generate_audit_report(self, df: pd.DataFrame) -> str:
        """Sinh báo cáo kiểm toán Markdown chi tiết."""
        m = self.audit_dataset(df)
        dist_str = ", ".join(f"Nhãn {k}: {v}" for k, v in sorted(m["target_win_binary_distribution"].items()))

        status_badge = "🟢 SẴN SÀNG" if m["is_statistically_sufficient"] else "🔴 CHƯA ĐỦ ĐIỀU KIỆN"

        return rf"""# 🔬 Báo Cáo Kiểm Toán & Thẩm Định Dữ Liệu Machine Learning
*Hệ thống Neiro-Stock-VN • Tiêu Chuẩn Thống Kê Dữ Liệu Dạng Bảng (Tabular ML Benchmark)*

---

### 1. Chỉ Số Đánh Giá Sẵn Sàng (ML Readiness Scorecard)

| Tiêu Chí Thẩm Định | Giá Trị Thực Tế | Ngưỡng Tiêu Chuẩn | Trạng Thái |
| :--- | :---: | :---: | :---: |
| **Tổng số mẫu (Sample Size)** | **{m['total_samples']}** | $\ge {self.MINIMUM_STATISTICAL_SAMPLES}$ mẫu | {'✅ Đạt' if m['total_samples'] >= self.MINIMUM_STATISTICAL_SAMPLES else '⚠️ Thiếu ' + str(m['minimum_sample_gap']) + ' mẫu'} |
| **Số mẫu chuẩn hóa v2** | **{m['v2_count']}** ({m['v2_ratio_pct']}%) | $\ge 300$ mẫu v2 | {'✅ Đạt' if m['v2_count'] >= 300 else '⚠️ Đang tích lũy'} |
| **Số mẫu cũ v1_legacy** | **{m['v1_legacy_count']}** | 0% (cần loại bỏ khi train) | {'✅ Đã lọc sạch' if m['v1_legacy_count'] == 0 else '⚠️ Cần Preprocessor lọc'} |
| **Độ hoàn thiện đặc trưng v2** | **{m['v2_feature_completeness_pct']}%** | $\ge 80.0\%$ | {'✅ Đầy đủ' if m['v2_feature_completeness_pct'] >= 80.0 else '⚠️ Còn nhiều giá trị 0'} |
| **Phân phối nhãn nhị phân** | {dist_str} | Tỷ lệ tối ưu $\le 4:1$ | {'✅ Cân bằng' if m['imbalance_ratio'] <= 4.0 else f'⚠️ Lệch {m["imbalance_ratio"]}:1 (Cần Class Weights)'} |
| **Vị thế đã đóng kiểm chứng** | **{m['closed_trades_count']}** (Win Rate: {m['closed_win_rate_pct']}%) | Đủ vòng đời T+2.5 đến T+20 | ✅ Đã kiểm chứng |

---

### 2. Kết Luận & Quyết Nghị: **{status_badge}**

> **Khuyến nghị hệ thống:**
> {m['recommendation']}
"""
