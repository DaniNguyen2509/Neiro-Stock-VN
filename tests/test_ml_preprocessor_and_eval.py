"""Kiểm thử TDD cho Bộ Chuẩn Hóa ML (ML Preprocessor) & Khung Đánh Giá Dữ Liệu (ADR-022)."""

import pandas as pd
import numpy as np
import pytest

from src.ml.preprocessor import MLSignalPreprocessor
from src.ml.dataset_validator import MLDatasetValidator


@pytest.fixture
def sample_dataset_df():
    """Tạo DataFrame mẫu giả lập tập dữ liệu ML của Neiro-Stock-VN."""
    return pd.DataFrame({
        "symbol": ["HPG", "SSI", "VCB", "FPT", "MWG", "DGC", "VIX", "CTS"],
        "first_signal_date": [
            "2026-10-20 09:30:00",
            "2026-10-21 09:30:00",
            "2026-10-22 09:30:00",
            "2026-10-23 09:30:00",
            "2026-10-26 09:30:00",
            "2026-10-27 09:30:00",
            "2026-10-28 09:30:00",
            "2026-10-29 09:30:00",
        ],
        "schema_version": ["v1_legacy", "v1_legacy", "v1_legacy", "v1_legacy", "v1_legacy", "v2", "v2", "v2"],
        "trading_days": [6, 5, 4, 3, 2, 2, 1, 0],
        "entry_original": [20.0, 25.0, 90.0, 100.0, 50.0, 80.0, 12.0, 30.0],
        "current_price": [22.0, 23.5, 92.0, 95.0, 48.0, 84.0, 11.5, 30.0],
        "pnl_pct": [10.0, -6.0, 2.2, -5.0, -4.0, 5.0, -4.1, 0.0],
        "target_win_binary": [1, 0, 0, 0, 0, 1, 0, 0],
        "outcome_label": ["WIN_TP2", "STOP_LOSS", "ACTIVE", "STOP_LOSS", "ACTIVE", "ACTIVE", "ACTIVE", "ACTIVE"],
        "is_closed": [True, True, False, True, False, False, False, False],
        "is_ml_ready": [True, True, False, True, False, False, False, False],
        "pe_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 12.5, 15.0, 14.2],
        "pb_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 1.8, 2.1, 1.9],
        "eps_ttm_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 4500.0, 1100.0, 2200.0],
        "camel_score_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "atr_pct_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 2.1, 3.4, 2.8],
        "atr_dist_from_poc_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 0.3, -0.4, 0.8],
        "market_breadth_pct_t0": [55.0, 52.0, 48.0, 45.0, 42.0, 60.0, 58.0, 56.0],
        "vn30_basis_t0": [0.0, 0.0, 0.0, 0.0, 0.0, 1.5, -2.0, 0.5],
        "adtv20_billion": [30.0, 25.0, 40.0, 35.0, 20.0, 15.0, 18.0, 22.0],
    })


class TestMLSignalPreprocessor:
    """Kiểm thử pipeline tiền xử lý và chuẩn hóa dữ liệu định lượng ML."""

    def test_clean_and_filter_schema(self, sample_dataset_df):
        preprocessor = MLSignalPreprocessor()
        
        # Test 1: Lọc bình thường không drop v1_legacy
        cleaned = preprocessor.clean_and_filter_schema(sample_dataset_df, drop_legacy=False)
        assert len(cleaned) == 8
        assert cleaned["pe_t0"].dtype in (float, np.float64)

        # Test 2: Lọc drop v1_legacy chỉ giữ v2 chuẩn
        v2_only = preprocessor.clean_and_filter_schema(sample_dataset_df, drop_legacy=True)
        assert len(v2_only) == 3
        assert set(v2_only["schema_version"].unique()) == {"v2"}

        # Test 3: Lọc theo số phiên giao dịch tối thiểu
        min_2d = preprocessor.clean_and_filter_schema(sample_dataset_df, min_trading_days=2)
        assert len(min_2d) == 6
        assert (min_2d["trading_days"] >= 2).all()

    def test_winsorize_features(self, sample_dataset_df):
        preprocessor = MLSignalPreprocessor()
        df = sample_dataset_df.copy()
        # Tạo giá trị ngoại lai cực đoan
        df.loc[0, "adtv20_billion"] = 1000.0
        
        w_df = preprocessor.winsorize_dataframe(df, columns=["adtv20_billion"], lower_q=0.05, upper_q=0.95)
        # Giá trị 1000.0 phải bị co về ngưỡng phân vị 95%
        assert w_df.loc[0, "adtv20_billion"] < 1000.0
        assert w_df.loc[0, "adtv20_billion"] > 35.0

    def test_robust_scale_dataframe(self, sample_dataset_df):
        preprocessor = MLSignalPreprocessor()
        scaled_df = preprocessor.robust_scale_dataframe(sample_dataset_df, columns=["adtv20_billion", "market_breadth_pct_t0"])
        
        # Robust Scaler: Trung vị sau chuẩn hóa phải xấp xỉ 0.0
        assert np.isclose(scaled_df["adtv20_billion"].median(), 0.0, atol=1e-5)
        assert np.isclose(scaled_df["market_breadth_pct_t0"].median(), 0.0, atol=1e-5)

    def test_calculate_class_weights(self):
        preprocessor = MLSignalPreprocessor()
        # Tập nhãn mất cân bằng: 90 số 0 và 10 số 1 (tổng 100 mẫu)
        y = pd.Series([0] * 90 + [1] * 10)
        weights = preprocessor.calculate_class_weights(y)
        
        assert 0 in weights and 1 in weights
        # Lớp thiểu số (1) phải có trọng số cao hơn lớp đa số (0) gấp 9 lần
        assert np.isclose(weights[1] / weights[0], 9.0)

    def test_purged_train_test_split_prevents_leakage(self, sample_dataset_df):
        preprocessor = MLSignalPreprocessor()
        train_df, test_df = preprocessor.purged_train_test_split(
            sample_dataset_df,
            date_column="first_signal_date",
            test_ratio=0.35,
            purge_window_sessions=2,
        )
        
        # Test set phải ở tương lai so với Train set
        max_train_date = pd.to_datetime(train_df["first_signal_date"]).max()
        min_test_date = pd.to_datetime(test_df["first_signal_date"]).min()
        assert max_train_date < min_test_date
        
        # Tổng số mẫu train + test phải nhỏ hơn hoặc bằng tổng mẫu ban đầu (do có các mẫu trong vùng purge bị loại)
        assert len(train_df) + len(test_df) <= len(sample_dataset_df)


class TestMLDatasetValidator:
    """Kiểm thử module Thẩm định và Đo lường Độ Sẵn Sàng ML."""

    def test_audit_dataset_metrics(self, sample_dataset_df):
        validator = MLDatasetValidator()
        audit = validator.audit_dataset(sample_dataset_df)
        
        assert audit["total_samples"] == 8
        assert audit["v1_legacy_count"] == 5
        assert audit["v2_count"] == 3
        assert audit["target_win_binary_distribution"] == {0: 6, 1: 2}
        assert audit["imbalance_ratio"] == 3.0  # 6 / 2
        assert audit["closed_trades_count"] == 3
        assert audit["is_statistically_sufficient"] is False
        assert audit["minimum_sample_gap"] > 0

    def test_generate_audit_report(self, sample_dataset_df):
        validator = MLDatasetValidator()
        report = validator.generate_audit_report(sample_dataset_df)
        
        assert "# 🔬 Báo Cáo Kiểm Toán & Thẩm Định Dữ Liệu Machine Learning" in report
        assert "**8**" in report
        assert "CHƯA ĐỦ ĐIỀU KIỆN" in report


class TestSystemAndMLEvaluationScript:
    """Kiểm thử script đánh giá toàn diện hệ thống & ML."""

    def test_evaluate_system_and_ml_execution(self, tmp_path):
        from scripts.evaluate_system_and_ml import run_comprehensive_evaluation
        output_report = tmp_path / "test_eval_report.md"
        
        report_text = run_comprehensive_evaluation(output_path=output_report)
        assert output_report.exists()
        assert "# 📊 Báo Cáo Đánh Giá Toàn Diện Hệ Thống & Machine Learning" in report_text
        assert "Walk-Forward Backtesting (2021 - 2026)" in report_text
        assert "Sổ Cái Tín Hiệu Thực Tế" in report_text
        assert "Thẩm Định Dữ Liệu Machine Learning" in report_text

