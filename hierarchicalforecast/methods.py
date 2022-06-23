# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/methods.ipynb (unless otherwise specified).

__all__ = ['bottom_up', 'BottomUp', 'top_down', 'TopDown', 'crossprod', 'min_trace', 'MinTrace', 'erm', 'ERM']

# Cell
from typing import List

import numpy as np
from statsmodels.stats.moment_helpers import cov2corr

# Cell
def _reconcile(S: np.ndarray, P: np.ndarray, W: np.ndarray,
               y_hat: np.ndarray, SP: np.ndarray = None):
    if SP is None:
        SP = S @ P
    return np.matmul(SP, y_hat)

# Cell
def bottom_up(S: np.ndarray,
              y_hat: np.ndarray):
    n_hiers, n_bottom = S.shape
    P = np.eye(n_bottom, n_hiers, k=(n_hiers - n_bottom), dtype=np.float32)
    W = np.eye(n_hiers, dtype=np.float32)
    return _reconcile(S, P, W, y_hat)

# Cell
class BottomUp:

    def reconcile(self,
                  S: np.ndarray,
                  y_hat: np.ndarray):
        return bottom_up(S=S, y_hat=y_hat)

    __call__ = reconcile

# Cell
def top_down(S: np.ndarray,
             y_hat: np.ndarray,
             y: np.ndarray,
             idx_bottom: List[int],
             method: str):
    n_hiers, n_bottom = S.shape
    idx_top = int(S.sum(axis=1).argmax())
    #add strictly hierarchical assert

    if method == 'forecast_proportions':
        raise NotImplementedError(f'Method {method} not implemented yet')
    else:
        y_top = y[idx_top]
        y_btm = y[idx_bottom]
        if method == 'average_proportions':
            prop = np.mean(y_btm / y_top, axis=1)
        elif method == 'proportion_averages':
            prop = np.mean(y_btm, axis=1) / np.mean(y_top)
        else:
            raise Exception(f'Unknown method {method}')
    P = np.zeros_like(S).T
    P[:, idx_top] = prop
    W = np.eye(n_hiers, dtype=np.float32)
    return _reconcile(S, P, W, y_hat)

# Cell
class TopDown:

    def __init__(self, method: str):
        self.method = method

    def reconcile(self,
                  S: np.ndarray,
                  y_hat: np.ndarray,
                  y: np.ndarray,
                  idx_bottom: List[int]):
        return top_down(S=S, y_hat=y_hat, y=y,
                        idx_bottom=idx_bottom,
                        method=self.method)

    __call__ = reconcile

# Cell
def crossprod(x):
    return x.T @ x

# Cell
def min_trace(S: np.ndarray,
              y_hat: np.ndarray,
              residuals: np.ndarray,
              method: str):
    # shape residuals (obs, n_hiers)
    res_methods = ['wls_var', 'mint_cov', 'mint_shrink']
    if method in res_methods and residuals is None:
        raise ValueError(f"For methods {', '.join(res_methods)} you need to pass residuals")
    n_hiers, n_bottom = S.shape
    if method == 'ols':
        W = np.eye(n_hiers)
    elif method == 'wls_struct':
        W = np.diag(S @ np.ones((n_bottom,)))
    elif method in res_methods:
        n, _ = residuals.shape
        masked_res = np.ma.array(residuals, mask=np.isnan(residuals))
        covm = np.ma.cov(masked_res, rowvar=False, allow_masked=True).data
        if method == 'wls_var':
            W = np.diag(np.diag(covm))
        elif method == 'mint_cov':
            W = covm
        elif method == 'mint_shrink':
            tar = np.diag(np.diag(covm))
            corm = cov2corr(covm)
            xs = np.divide(residuals, np.sqrt(np.diag(covm)))
            xs = xs[~np.isnan(xs).any(axis=1), :]
            v = (1 / (n * (n - 1))) * (crossprod(xs ** 2) - (1 / n) * (crossprod(xs) ** 2))
            np.fill_diagonal(v, 0)
            corapn = cov2corr(tar)
            d = (corm - corapn) ** 2
            lmd = v.sum() / d.sum()
            lmd = max(min(lmd, 1), 0)
            W = lmd * tar + (1 - lmd) * covm
    else:
        raise ValueError(f'Unkown reconciliation method {method}')

    eigenvalues, _ = np.linalg.eig(W)
    if any(eigenvalues < 1e-8):
        raise Exception(f'min_trace ({method}) needs covariance matrix to be positive definite.')

    R = S.T @ np.linalg.inv(W)
    P = np.linalg.inv(R @ S) @ R

    return _reconcile(S, P, W, y_hat)

# Cell
class MinTrace:

    def __init__(self, method: str):
        self.method = method

    def reconcile(self,
                  S: np.ndarray,
                  y_hat: np.ndarray,
                  residuals: np.ndarray):
        return min_trace(S=S, y_hat=y_hat,
                         residuals=residuals,
                         method=self.method)

    __call__ = reconcile

# Cell
def erm(S: np.ndarray,
        y_hat: np.ndarray,
        method: str,
        lambda_reg: float = 1e-2):
    n_hiers, n_bottom = S.shape
    if method == 'exact':
        B = y_hat.T @ S @ np.linalg.inv(S.T @ S).T
        P = B.T @ y_hat.T @ np.linalg.inv(y_hat @ y_hat.T + lambda_reg * np.eye(n_hiers))
    else:
        raise ValueError(f'Unkown reconciliation method {method}')

    W = np.eye(n_hiers, dtype=np.float32)

    return _reconcile(S, P, W, y_hat)

# Cell
class ERM:

    def __init__(self, method: str, lambda_reg: float = 1e-2):
        self.method = method
        self.lambda_reg = lambda_reg

    def reconcile(self, S: np.ndarray,
                  y_hat: np.ndarray):
        return erm(S=S, y_hat=y_hat,
                   method=self.method, lambda_reg=self.lambda_reg)

    __call__ = reconcile