"""Bộ Chuẩn Hóa và Tiền Xử Lý Dữ Liệu Machine Learning (ML Signal Preprocessor - ADR-022).

Thực hiện toàn bộ quy trình tiền xử lý định lượng bằng pure NumPy và Pandas:
1. Xử lý lệch pha cấu trúc dữ liệu (Schema Drift): Lọc bỏ hoặc chuẩn hóa v1_legacy vs v2.
2. Xử lý ngoại lai tài chính (Outlier Winsorization): Cắt xén đuôi nặng phân vị 1% - 99%.
3. Chuẩn hóa Robust Scaling: Chuẩn hóa theo Trung vị (Median) và IQR, chống méo lệch do biến động sàn.
4. Cân bằng trọng số mẫu (Class Weights): Đối phó với mất cân bằng nhãn trầm trọng (Severe Class Imbalance).
5. Bộ chia dữ liệu chuỗi thời gian có đệm thanh toán T+2.5 (Purged Time-Series Split): Chống rò rỉ dữ liệu (Lookahead Leakage).
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class MLSignalPreprocessor:
    """Bộ tiền xử lý và chuẩn hóa dữ liệu định lượng phục vụ mô hình Machine Learning."""

    def clean_and_filter_schema(
        self,
        df: pd.DataFrame,
        drop_legacy: bool = False,
        min_trading_days: int = 0,
    ) -> pd.DataFrame:
        """Làm sạch và lọc các mẫu dữ liệu theo phiên bản cấu trúc (Schema) và số phiên quan sát.
        
        Args:
            df: DataFrame đầu vào.
            drop_legacy: Nếu True, loại bỏ hoàn toàn các bản ghi v1_legacy thiếu đặc trưng T0.
            min_trading_days: Số phiên giao dịch thực tế tối thiểu để mẫu được giữ lại.
            
        Returns:
            DataFrame đã làm sạch.
        """
        res = df.copy()

        if drop_legacy and "schema_version" in res.columns:
            res = res[res["schema_version"] == "v2"]

        if min_trading_days > 0 and "trading_days" in res.columns:
            res = res[res["trading_days"] >= min_trading_days]

        numeric_cols = [
            "entry_original", "current_price", "pnl_pct", "trading_days",
            "pe_t0", "pb_t0", "eps_ttm_t0", "camel_score_t0", "atr_pct_t0",
            "atr_dist_from_poc_t0", "market_breadth_pct_t0", "vn30_basis_t0",
            "adtv20_billion", "target_win_binary"
        ]
        for col in numeric_cols:
            if col in res.columns:
                res[col] = pd.to_numeric(res[col], errors="coerce").fillna(0.0)

        return res.reset_index(drop=True)

    def winsorize_series(
        self,
        series: pd.Series,
        lower_q: float = 0.01,
        upper_q: float = 0.99,
    ) -> pd.Series:
        """Cắt xén giá trị ngoại lai của Series theo phân vị lower_q và upper_q."""
        s = series.copy()
        low_val = s.quantile(lower_q)
        high_val = s.quantile(upper_q)
        return s.clip(lower=low_val, upper=high_val)

    def winsorize_dataframe(
        self,
        df: pd.DataFrame,
        columns: List[str],
        lower_q: float = 0.01,
        upper_q: float = 0.99,
    ) -> pd.DataFrame:
        """Cắt xén giá trị ngoại lai cho danh sách các cột trong DataFrame."""
        res = df.copy()
        for col in columns:
            if col in res.columns and pd.api.types.is_numeric_dtype(res[col]):
                res[col] = self.winsorize_series(res[col], lower_q=lower_q, upper_q=upper_q)
        return res

    def robust_scale_series(self, series: pd.Series) -> pd.Series:
        """Chuẩn hóa Robust Scaling: (x - median) / IQR. Nếu IQR == 0 trả về zeros."""
        s = pd.to_numeric(series.copy(), errors="coerce").fillna(0.0)
        med = s.median()
        q75 = s.quantile(0.75)
        q25 = s.quantile(0.25)
        iqr = q75 - q25
        if np.isclose(iqr, 0.0) or np.isnan(iqr):
            return s - med
        return (s - med) / iqr

    def robust_scale_dataframe(
        self,
        df: pd.DataFrame,
        columns: List[str],
    ) -> pd.DataFrame:
        """Chuẩn hóa Robust Scaling cho danh sách các cột đặc trưng."""
        res = df.copy()
        for col in columns:
            if col in res.columns:
                res[col] = self.robust_scale_series(res[col])
        return res

    def calculate_class_weights(self, y: pd.Series) -> Dict[int, float]:
        """Tính toán trọng số cân bằng lớp mẫu: w_j = N / (K * n_j)."""
        s = pd.Series(y).dropna().astype(int)
        n_samples = len(s)
        classes = sorted(s.unique())
        n_classes = len(classes)
        if n_classes <= 1 or n_samples == 0:
            return {c: 1.0 for c in classes}

        weights: Dict[int, float] = {}
        for c in classes:
            count = (s == c).sum()
            weights[c] = float(n_samples / (n_classes * count)) if count > 0 else 1.0
        return weights

    def purged_train_test_split(
        self,
        df: pd.DataFrame,
        date_column: str = "first_signal_date",
        test_ratio: float = 0.25,
        purge_window_sessions: int = 3,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Chia tập dữ liệu theo chuỗi thời gian có đệm thanh toán T+2.5 (Purge Window).
        
        Khoảng đệm (purge_window_sessions) loại bỏ các mẫu tại ranh giới cuối tập Train
        để ngăn chặn thông tin chu kỳ thanh toán T+2.5 bị rò rỉ sang tập Test.
        """
        if len(df) == 0:
            return df.copy(), df.copy()

        res = df.copy()
        if date_column in res.columns:
            res = res.sort_values(by=date_column).reset_index(drop=True)

        n = len(res)
        split_idx = int(n * (1.0 - test_ratio))
        split_idx = max(1, min(split_idx, n - 1))

        test_df = res.iloc[split_idx:].reset_index(drop=True)

        # Purging: Loại bỏ purge_window_sessions mẫu cuối của train set sát ranh giới test set
        purge_end_idx = max(1, split_idx - purge_window_sessions)
        train_df = res.iloc[:purge_end_idx].reset_index(drop=True)

        return train_df, test_df
