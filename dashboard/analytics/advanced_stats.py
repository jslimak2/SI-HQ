"""
Advanced Statistical Analysis for Sports Betting
Professional-grade statistical methods and analysis
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
from scipy.optimize import minimize
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from arch import arch_model
from sklearn.metrics import sharpe_ratio
import warnings
warnings.filterwarnings('ignore')

from typing import Dict, List, Tuple, Optional, Any
import json
from datetime import datetime, timedelta


class AdvancedSportsAnalyzer:
    """Professional sports statistical analysis system"""
    
    def __init__(self, sport: str = 'NBA'):
        self.sport = sport.upper()
        self.confidence_level = 0.95
        
    def calculate_kelly_criterion(self, win_probability: float, odds: float, 
                                bankroll: float = 1000) -> Dict[str, float]:
        """Calculate optimal bet size using Kelly Criterion"""
        
        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly formula: f* = (bp - q) / b
        # where b = odds-1, p = win probability, q = 1-p
        b = decimal_odds - 1
        p = win_probability
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Ensure non-negative fraction (don't bet if negative expected value)
        kelly_fraction = max(0, kelly_fraction)
        
        # Calculate bet amounts
        full_kelly = bankroll * kelly_fraction
        half_kelly = full_kelly * 0.5  # Conservative approach
        quarter_kelly = full_kelly * 0.25  # Very conservative
        
        # Expected value calculation
        expected_value = (p * b * full_kelly) - (q * full_kelly)
        
        return {
            'kelly_fraction': kelly_fraction,
            'full_kelly_bet': full_kelly,
            'half_kelly_bet': half_kelly,
            'quarter_kelly_bet': quarter_kelly,
            'expected_value': expected_value,
            'expected_roi': expected_value / bankroll if bankroll > 0 else 0,
            'recommendation': self._get_kelly_recommendation(kelly_fraction)
        }
    
    def _get_kelly_recommendation(self, kelly_fraction: float) -> str:
        """Get betting recommendation based on Kelly fraction"""
        if kelly_fraction <= 0:
            return "No bet - negative expected value"
        elif kelly_fraction < 0.02:
            return "Small bet - minimal edge"
        elif kelly_fraction < 0.05:
            return "Moderate bet - decent edge"
        elif kelly_fraction < 0.10:
            return "Strong bet - good edge"
        else:
            return "Very strong bet - excellent edge"
    
    def calculate_confidence_intervals(self, data: np.ndarray, 
                                     confidence_level: float = 0.95) -> Dict[str, float]:
        """Calculate confidence intervals for betting statistics"""
        
        mean = np.mean(data)
        std_error = stats.sem(data)  # Standard error of the mean
        
        # Calculate confidence interval
        ci = stats.t.interval(
            confidence_level,
            df=len(data) - 1,
            loc=mean,
            scale=std_error
        )
        
        return {
            'mean': mean,
            'std_error': std_error,
            'confidence_level': confidence_level,
            'lower_bound': ci[0],
            'upper_bound': ci[1],
            'margin_of_error': ci[1] - mean
        }
    
    def perform_regression_analysis(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Perform regression analysis to identify key factors"""
        
        # Add constant term for intercept
        X_with_const = sm.add_constant(X)
        
        # Fit OLS model
        model = sm.OLS(y, X_with_const).fit()
        
        # Calculate additional statistics
        vif_data = pd.DataFrame()
        if len(X.columns) > 1:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            vif_data["Feature"] = X.columns
            vif_data["VIF"] = [variance_inflation_factor(X.values, i) 
                              for i in range(X.shape[1])]
        
        # Feature importance based on coefficients and p-values
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'coefficient': model.params[1:],  # Exclude intercept
            'p_value': model.pvalues[1:],
            'significant': model.pvalues[1:] < 0.05
        }).sort_values('coefficient', key=abs, ascending=False)
        
        return {
            'model_summary': str(model.summary()),
            'r_squared': model.rsquared,
            'adjusted_r_squared': model.rsquared_adj,
            'f_statistic': model.fvalue,
            'f_pvalue': model.f_pvalue,
            'feature_importance': feature_importance.to_dict('records'),
            'vif_scores': vif_data.to_dict('records') if not vif_data.empty else [],
            'residuals': model.resid.tolist(),
            'fitted_values': model.fittedvalues.tolist()
        }
    
    def calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio for betting strategy performance"""
        
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
    
    def calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        
        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0 or np.std(downside_returns) == 0:
            return 0.0
        
        return np.mean(excess_returns) / np.std(downside_returns) * np.sqrt(252)
    
    def calculate_maximum_drawdown(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate maximum drawdown and related metrics"""
        
        cumulative_returns = np.cumprod(1 + returns)
        rolling_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        
        max_drawdown = np.min(drawdown)
        max_drawdown_idx = np.argmin(drawdown)
        
        # Find peak before max drawdown
        peak_idx = np.argmax(rolling_max[:max_drawdown_idx+1])
        
        # Find recovery point (if any)
        recovery_idx = None
        peak_value = rolling_max[peak_idx]
        for i in range(max_drawdown_idx, len(cumulative_returns)):
            if cumulative_returns[i] >= peak_value:
                recovery_idx = i
                break
        
        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_drawdown_idx - peak_idx if peak_idx < max_drawdown_idx else 0,
            'recovery_duration': recovery_idx - max_drawdown_idx if recovery_idx else None,
            'current_drawdown': drawdown[-1],
            'drawdown_series': drawdown.tolist()
        }
    
    def perform_value_at_risk_analysis(self, returns: np.ndarray, 
                                     confidence_levels: List[float] = [0.95, 0.99]) -> Dict[str, float]:
        """Calculate Value at Risk (VaR) and Conditional VaR"""
        
        var_results = {}
        
        for confidence_level in confidence_levels:
            # Historical VaR (percentile method)
            var_historical = np.percentile(returns, (1 - confidence_level) * 100)
            
            # Parametric VaR (assuming normal distribution)
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            var_parametric = mean_return - stats.norm.ppf(confidence_level) * std_return
            
            # Conditional VaR (Expected Shortfall)
            cvar = np.mean(returns[returns <= var_historical])
            
            var_results[f'var_{int(confidence_level*100)}'] = {
                'historical_var': var_historical,
                'parametric_var': var_parametric,
                'conditional_var': cvar
            }
        
        return var_results
    
    def analyze_betting_streaks(self, outcomes: List[str]) -> Dict[str, Any]:
        """Analyze winning and losing streaks"""
        
        # Convert outcomes to binary (1 for win, 0 for loss)
        binary_outcomes = [1 if outcome.lower() in ['win', 'w', 'won'] else 0 
                          for outcome in outcomes]
        
        if not binary_outcomes:
            return {'error': 'No outcomes provided'}
        
        # Find streaks
        streaks = []
        current_streak = 1
        current_type = binary_outcomes[0]
        
        for i in range(1, len(binary_outcomes)):
            if binary_outcomes[i] == current_type:
                current_streak += 1
            else:
                streaks.append({
                    'type': 'win' if current_type == 1 else 'loss',
                    'length': current_streak
                })
                current_streak = 1
                current_type = binary_outcomes[i]
        
        # Add final streak
        streaks.append({
            'type': 'win' if current_type == 1 else 'loss',
            'length': current_streak
        })
        
        # Analyze streaks
        win_streaks = [s['length'] for s in streaks if s['type'] == 'win']
        loss_streaks = [s['length'] for s in streaks if s['type'] == 'loss']
        
        return {
            'total_bets': len(binary_outcomes),
            'total_wins': sum(binary_outcomes),
            'win_rate': np.mean(binary_outcomes),
            'longest_win_streak': max(win_streaks) if win_streaks else 0,
            'longest_loss_streak': max(loss_streaks) if loss_streaks else 0,
            'avg_win_streak': np.mean(win_streaks) if win_streaks else 0,
            'avg_loss_streak': np.mean(loss_streaks) if loss_streaks else 0,
            'current_streak': {
                'type': streaks[-1]['type'],
                'length': streaks[-1]['length']
            },
            'streak_distribution': {
                'win_streaks': win_streaks,
                'loss_streaks': loss_streaks
            }
        }
    
    def calculate_portfolio_metrics(self, strategy_returns: Dict[str, np.ndarray], 
                                  weights: Dict[str, float] = None) -> Dict[str, Any]:
        """Calculate portfolio-level metrics for multiple betting strategies"""
        
        if weights is None:
            # Equal weights
            weights = {strategy: 1/len(strategy_returns) 
                      for strategy in strategy_returns.keys()}
        
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v/total_weight for k, v in weights.items()}
        
        # Calculate portfolio returns
        portfolio_returns = np.zeros(len(list(strategy_returns.values())[0]))
        
        for strategy, returns in strategy_returns.items():
            portfolio_returns += weights[strategy] * returns
        
        # Calculate metrics
        annual_return = np.mean(portfolio_returns) * 252
        annual_volatility = np.std(portfolio_returns) * np.sqrt(252)
        sharpe = self.calculate_sharpe_ratio(portfolio_returns)
        sortino = self.calculate_sortino_ratio(portfolio_returns)
        max_dd = self.calculate_maximum_drawdown(portfolio_returns)
        
        # Calculate correlations between strategies
        correlations = {}
        strategy_names = list(strategy_returns.keys())
        
        for i, strategy1 in enumerate(strategy_names):
            for strategy2 in strategy_names[i+1:]:
                corr = np.corrcoef(strategy_returns[strategy1], 
                                 strategy_returns[strategy2])[0, 1]
                correlations[f"{strategy1}_vs_{strategy2}"] = corr
        
        return {
            'portfolio_metrics': {
                'annual_return': annual_return,
                'annual_volatility': annual_volatility,
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'max_drawdown': max_dd['max_drawdown'],
                'calmar_ratio': annual_return / abs(max_dd['max_drawdown']) if max_dd['max_drawdown'] != 0 else 0
            },
            'strategy_weights': weights,
            'strategy_correlations': correlations,
            'diversification_ratio': self._calculate_diversification_ratio(strategy_returns, weights)
        }
    
    def _calculate_diversification_ratio(self, strategy_returns: Dict[str, np.ndarray], 
                                       weights: Dict[str, float]) -> float:
        """Calculate portfolio diversification ratio"""
        
        # Weighted average of individual volatilities
        weighted_vol = sum(weights[strategy] * np.std(returns) * np.sqrt(252) 
                          for strategy, returns in strategy_returns.items())
        
        # Portfolio volatility
        portfolio_returns = np.zeros(len(list(strategy_returns.values())[0]))
        for strategy, returns in strategy_returns.items():
            portfolio_returns += weights[strategy] * returns
        
        portfolio_vol = np.std(portfolio_returns) * np.sqrt(252)
        
        return weighted_vol / portfolio_vol if portfolio_vol != 0 else 1.0
    
    def optimize_portfolio_weights(self, strategy_returns: Dict[str, np.ndarray], 
                                 target_return: float = None) -> Dict[str, Any]:
        """Optimize portfolio weights using mean-variance optimization"""
        
        strategies = list(strategy_returns.keys())
        returns_matrix = np.array([strategy_returns[s] for s in strategies])
        
        # Calculate expected returns and covariance matrix
        expected_returns = np.mean(returns_matrix, axis=1) * 252  # Annualized
        cov_matrix = np.cov(returns_matrix) * 252  # Annualized
        
        n_assets = len(strategies)
        
        # Objective function (minimize variance)
        def objective(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        if target_return is not None:
            constraints.append({
                'type': 'eq', 
                'fun': lambda x: np.dot(x, expected_returns) - target_return
            })
        
        # Bounds (no short selling)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess (equal weights)
        x0 = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            optimal_weights = {strategy: float(weight) 
                             for strategy, weight in zip(strategies, result.x)}
            
            # Calculate metrics for optimal portfolio
            optimal_return = np.dot(result.x, expected_returns)
            optimal_volatility = np.sqrt(objective(result.x))
            optimal_sharpe = optimal_return / optimal_volatility if optimal_volatility != 0 else 0
            
            return {
                'optimal_weights': optimal_weights,
                'expected_return': optimal_return,
                'expected_volatility': optimal_volatility,
                'expected_sharpe': optimal_sharpe,
                'optimization_success': True
            }
        else:
            return {
                'optimization_success': False,
                'error': result.message
            }
    
    def generate_advanced_visualizations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate advanced statistical visualizations"""
        
        visualizations = {}
        
        # 1. Performance Attribution Chart
        if 'strategy_returns' in data:
            fig_attribution = self._create_attribution_chart(data['strategy_returns'])
            visualizations['performance_attribution'] = fig_attribution
        
        # 2. Risk-Return Scatter Plot
        if 'strategies_metrics' in data:
            fig_risk_return = self._create_risk_return_chart(data['strategies_metrics'])
            visualizations['risk_return_analysis'] = fig_risk_return
        
        # 3. Drawdown Analysis
        if 'returns' in data:
            fig_drawdown = self._create_drawdown_chart(data['returns'])
            visualizations['drawdown_analysis'] = fig_drawdown
        
        # 4. Rolling Statistics
        if 'returns' in data:
            fig_rolling = self._create_rolling_stats_chart(data['returns'])
            visualizations['rolling_statistics'] = fig_rolling
        
        return visualizations
    
    def _create_attribution_chart(self, strategy_returns: Dict[str, np.ndarray]) -> Dict:
        """Create performance attribution chart"""
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Cumulative Returns by Strategy', 'Monthly Returns Distribution'),
            vertical_spacing=0.12
        )
        
        # Cumulative returns
        for strategy, returns in strategy_returns.items():
            cumulative = np.cumprod(1 + returns)
            fig.add_trace(
                go.Scatter(
                    y=cumulative,
                    name=strategy,
                    mode='lines'
                ),
                row=1, col=1
            )
        
        # Returns distribution
        for strategy, returns in strategy_returns.items():
            fig.add_trace(
                go.Box(
                    y=returns * 100,  # Convert to percentage
                    name=strategy,
                    showlegend=False
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title='Strategy Performance Attribution',
            height=800,
            showlegend=True
        )
        
        return fig.to_dict()
    
    def _create_risk_return_chart(self, strategies_metrics: Dict[str, Dict]) -> Dict:
        """Create risk-return scatter plot"""
        
        strategies = []
        returns = []
        volatilities = []
        sharpes = []
        
        for strategy, metrics in strategies_metrics.items():
            strategies.append(strategy)
            returns.append(metrics.get('annual_return', 0))
            volatilities.append(metrics.get('annual_volatility', 0))
            sharpes.append(metrics.get('sharpe_ratio', 0))
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=volatilities,
            y=returns,
            mode='markers+text',
            text=strategies,
            textposition='top center',
            marker=dict(
                size=[abs(s)*20 + 10 for s in sharpes],  # Size based on Sharpe ratio
                color=sharpes,
                colorscale='RdYlGn',
                colorbar=dict(title="Sharpe Ratio"),
                line=dict(width=2, color='black')
            ),
            name='Strategies'
        ))
        
        fig.update_layout(
            title='Risk-Return Analysis',
            xaxis_title='Annual Volatility',
            yaxis_title='Annual Return',
            height=600
        )
        
        return fig.to_dict()
    
    def _create_drawdown_chart(self, returns: np.ndarray) -> Dict:
        """Create drawdown analysis chart"""
        
        max_dd_info = self.calculate_maximum_drawdown(returns)
        drawdown_series = max_dd_info['drawdown_series']
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Cumulative Returns', 'Drawdown Analysis'),
            vertical_spacing=0.12
        )
        
        # Cumulative returns
        cumulative_returns = np.cumprod(1 + returns)
        fig.add_trace(
            go.Scatter(
                y=cumulative_returns,
                name='Cumulative Returns',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # Drawdown
        fig.add_trace(
            go.Scatter(
                y=np.array(drawdown_series) * 100,  # Convert to percentage
                name='Drawdown %',
                fill='tozeroy',
                line=dict(color='red'),
                showlegend=False
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f'Drawdown Analysis (Max DD: {max_dd_info["max_drawdown"]*100:.2f}%)',
            height=800
        )
        
        return fig.to_dict()
    
    def _create_rolling_stats_chart(self, returns: np.ndarray, window: int = 30) -> Dict:
        """Create rolling statistics chart"""
        
        rolling_return = pd.Series(returns).rolling(window).mean() * 252
        rolling_volatility = pd.Series(returns).rolling(window).std() * np.sqrt(252)
        rolling_sharpe = rolling_return / rolling_volatility
        
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Rolling Annual Return', 'Rolling Annual Volatility', 'Rolling Sharpe Ratio'),
            vertical_spacing=0.08
        )
        
        # Rolling return
        fig.add_trace(
            go.Scatter(y=rolling_return, name='Rolling Return', line=dict(color='blue')),
            row=1, col=1
        )
        
        # Rolling volatility
        fig.add_trace(
            go.Scatter(y=rolling_volatility, name='Rolling Volatility', line=dict(color='orange')),
            row=2, col=1
        )
        
        # Rolling Sharpe
        fig.add_trace(
            go.Scatter(y=rolling_sharpe, name='Rolling Sharpe', line=dict(color='green')),
            row=3, col=1
        )
        
        fig.update_layout(
            title=f'{window}-Day Rolling Statistics',
            height=900,
            showlegend=False
        )
        
        return fig.to_dict()


def generate_demo_analytics_data() -> Dict[str, Any]:
    """Generate demo data for analytics testing"""
    np.random.seed(42)
    
    # Generate synthetic strategy returns
    n_days = 252  # One year of trading days
    
    strategies = {
        'momentum': np.random.normal(0.0008, 0.02, n_days),  # Slightly positive expected return
        'mean_reversion': np.random.normal(0.0006, 0.015, n_days),
        'arbitrage': np.random.normal(0.0004, 0.008, n_days),  # Lower volatility
        'value_betting': np.random.normal(0.001, 0.025, n_days)  # Higher volatility, higher return
    }
    
    # Add some correlation between strategies
    market_factor = np.random.normal(0, 0.01, n_days)
    for strategy in strategies:
        strategies[strategy] += 0.3 * market_factor  # 30% correlation with market
    
    # Generate betting outcomes
    outcomes = np.random.choice(['win', 'loss'], size=100, p=[0.55, 0.45])
    
    return {
        'strategy_returns': strategies,
        'betting_outcomes': outcomes.tolist(),
        'sample_bets': [
            {'amount': 100, 'odds': 1.85, 'outcome': 'win'},
            {'amount': 150, 'odds': 2.10, 'outcome': 'loss'},
            {'amount': 75, 'odds': 1.65, 'outcome': 'win'},
        ]
    }


if __name__ == "__main__":
    # Demo usage
    print("Advanced Sports Analytics Demo")
    print("=" * 40)
    
    analyzer = AdvancedSportsAnalyzer('NBA')
    demo_data = generate_demo_analytics_data()
    
    # Kelly Criterion example
    print("\n1. Kelly Criterion Analysis:")
    kelly_result = analyzer.calculate_kelly_criterion(0.58, 1.85, 1000)
    print(f"Win Probability: 58%, Odds: 1.85")
    print(f"Kelly Fraction: {kelly_result['kelly_fraction']:.3f}")
    print(f"Recommended Bet: ${kelly_result['half_kelly_bet']:.2f} (Half Kelly)")
    print(f"Expected ROI: {kelly_result['expected_roi']*100:.2f}%")
    
    # Confidence Intervals
    print("\n2. Confidence Interval Analysis:")
    sample_returns = demo_data['strategy_returns']['momentum']
    ci_result = analyzer.calculate_confidence_intervals(sample_returns)
    print(f"Mean Return: {ci_result['mean']*100:.3f}%")
    print(f"95% CI: [{ci_result['lower_bound']*100:.3f}%, {ci_result['upper_bound']*100:.3f}%]")
    
    # Risk Metrics
    print("\n3. Risk Analysis:")
    sharpe = analyzer.calculate_sharpe_ratio(sample_returns)
    sortino = analyzer.calculate_sortino_ratio(sample_returns)
    print(f"Sharpe Ratio: {sharpe:.3f}")
    print(f"Sortino Ratio: {sortino:.3f}")
    
    # Drawdown Analysis
    dd_result = analyzer.calculate_maximum_drawdown(sample_returns)
    print(f"Maximum Drawdown: {dd_result['max_drawdown']*100:.2f}%")
    
    # Portfolio Optimization
    print("\n4. Portfolio Optimization:")
    portfolio_result = analyzer.calculate_portfolio_metrics(demo_data['strategy_returns'])
    print(f"Portfolio Sharpe Ratio: {portfolio_result['portfolio_metrics']['sharpe_ratio']:.3f}")
    print(f"Diversification Ratio: {portfolio_result['diversification_ratio']:.3f}")
    
    # Betting Streaks
    print("\n5. Betting Streak Analysis:")
    streak_result = analyzer.analyze_betting_streaks(demo_data['betting_outcomes'])
    print(f"Win Rate: {streak_result['win_rate']*100:.1f}%")
    print(f"Longest Win Streak: {streak_result['longest_win_streak']}")
    print(f"Longest Loss Streak: {streak_result['longest_loss_streak']}")
    
    print("\nDemo completed successfully!")