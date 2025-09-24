"""
Weekly automation and user engagement system for Post9
"""
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

from error_handling import ValidationError, ExternalServiceError

logger = logging.getLogger(__name__)

@dataclass
class UserPreferences:
    """User preferences for weekly reports and notifications"""
    user_id: str
    email: str
    weekly_report_enabled: bool = True
    performance_alerts_enabled: bool = True
    model_updates_enabled: bool = True
    strategy_suggestions_enabled: bool = True
    preferred_day: str = "Monday"  # Day of week for weekly reports
    preferred_time: str = "09:00"  # Time for reports (24h format)
    risk_tolerance: str = "medium"  # low, medium, high
    favorite_sports: List[str] = None
    
    def __post_init__(self):
        if self.favorite_sports is None:
            self.favorite_sports = ["NBA", "NFL"]

@dataclass
class WeeklyReport:
    """Weekly performance and insights report"""
    user_id: str
    week_start: str
    week_end: str
    total_bets: int
    total_profit: float
    win_rate: float
    roi: float
    best_strategy: str
    worst_strategy: str
    top_opportunities: List[Dict[str, Any]]
    model_performance: Dict[str, Any]
    recommendations: List[str]
    risk_analysis: Dict[str, Any]
    generated_at: str

class NotificationService:
    """Professional notification service for user engagement"""
    
    def __init__(self, smtp_config: Dict[str, str] = None):
        self.smtp_config = smtp_config or {
            'server': 'localhost',
            'port': 587,
            'username': 'post9@example.com',
            'password': 'demo_password',
            'use_tls': True
        }
        self.templates = self._load_email_templates()
    
    def _load_email_templates(self) -> Dict[str, str]:
        """Load email templates for different notification types"""
        return {
            'weekly_report': """
            <html>
            <head><title>Post9 Weekly Performance Report</title></head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c3e50; text-align: center;">[ANALYTICS] Weekly Performance Report</h1>
                    
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #27ae60; margin-top: 0;">Performance Summary</h2>
                        <ul style="list-style: none; padding: 0;">
                            <li><strong>Total Bets:</strong> {total_bets}</li>
                            <li><strong>Win Rate:</strong> {win_rate:.1f}%</li>
                            <li><strong>Total Profit:</strong> ${total_profit:.2f}</li>
                            <li><strong>ROI:</strong> {roi:.1f}%</li>
                        </ul>
                    </div>
                    
                    <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #1976d2; margin-top: 0;">Strategy Performance</h2>
                        <p><strong>🏆 Best Strategy:</strong> {best_strategy}</p>
                        <p><strong>⚠️ Needs Attention:</strong> {worst_strategy}</p>
                    </div>
                    
                    <div style="background: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #f57c00; margin-top: 0;">[OPPORTUNITIES] This Week's Opportunities</h2>
                        {opportunities_html}
                    </div>
                    
                    <div style="background: #f3e5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h2 style="color: #7b1fa2; margin-top: 0;">💡 Recommendations</h2>
                        <ul>
                            {recommendations_html}
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                        <p style="color: #666;">
                            <strong>Post9</strong> - Stop Betting. Start Investing.<br>
                            <a href="http://localhost:5000" style="color: #2c3e50;">Visit Dashboard</a> | 
                            <a href="http://localhost:5000/ml" style="color: #2c3e50;">ML Dashboard</a>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """,
            
            'performance_alert': """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #e74c3c;">⚠️ Performance Alert</h1>
                    <p>We've detected some performance issues that need your attention:</p>
                    <div style="background: #ffebee; padding: 15px; border-radius: 5px; border-left: 4px solid #e74c3c;">
                        <p><strong>Alert:</strong> {alert_message}</p>
                        <p><strong>Recommendation:</strong> {recommendation}</p>
                    </div>
                    <p><a href="http://localhost:5000" style="color: #2c3e50;">Review your dashboard</a></p>
                </div>
            </body>
            </html>
            """,
            
            'model_update': """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #2c3e50;">🧠 Model Update Available</h1>
                    <p>A new version of your ML model is ready:</p>
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; border-left: 4px solid #27ae60;">
                        <p><strong>Model:</strong> {model_name}</p>
                        <p><strong>New Accuracy:</strong> {accuracy:.1f}%</p>
                        <p><strong>Improvement:</strong> +{improvement:.1f}%</p>
                    </div>
                    <p><a href="http://localhost:5000/ml" style="color: #2c3e50;">Update your model</a></p>
                </div>
            </body>
            </html>
            """
        }
    
    def send_weekly_report(self, user_preferences: UserPreferences, report: WeeklyReport) -> bool:
        """Send weekly performance report to user"""
        try:
            # Format opportunities HTML
            opportunities_html = ""
            for opp in report.top_opportunities:
                opportunities_html += f"""
                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 4px;">
                    <strong>{opp['teams']}</strong> - {opp['sport']}<br>
                    <span style="color: #27ae60;">Confidence: {opp['confidence']}%</span> | 
                    <span style="color: #2980b9;">Expected Value: +{opp['expected_value']}%</span>
                </div>
                """
            
            # Format recommendations HTML
            recommendations_html = ""
            for rec in report.recommendations:
                recommendations_html += f"<li>{rec}</li>"
            
            # Fill template
            html_content = self.templates['weekly_report'].format(
                total_bets=report.total_bets,
                win_rate=report.win_rate,
                total_profit=report.total_profit,
                roi=report.roi,
                best_strategy=report.best_strategy,
                worst_strategy=report.worst_strategy,
                opportunities_html=opportunities_html,
                recommendations_html=recommendations_html
            )
            
            subject = f"[ANALYTICS] Weekly Performance Report - Week of {report.week_start}"
            
            return self._send_email(user_preferences.email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send weekly report to {user_preferences.user_id}: {e}")
            return False
    
    def send_performance_alert(self, user_preferences: UserPreferences, alert_message: str, recommendation: str) -> bool:
        """Send performance alert notification"""
        try:
            html_content = self.templates['performance_alert'].format(
                alert_message=alert_message,
                recommendation=recommendation
            )
            
            subject = "⚠️ Post9 Performance Alert"
            
            return self._send_email(user_preferences.email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send performance alert to {user_preferences.user_id}: {e}")
            return False
    
    def send_model_update_notification(self, user_preferences: UserPreferences, model_name: str, 
                                     new_accuracy: float, improvement: float) -> bool:
        """Send model update notification"""
        try:
            html_content = self.templates['model_update'].format(
                model_name=model_name,
                accuracy=new_accuracy,
                improvement=improvement
            )
            
            subject = "🧠 Post9 Model Update Available"
            
            return self._send_email(user_preferences.email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send model update notification to {user_preferences.user_id}: {e}")
            return False
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SMTP (demo implementation)"""
        try:
            # In demo mode, just log the email instead of actually sending
            logger.info(f"Demo email sent to {to_email}")
            logger.info(f"Subject: {subject}")
            logger.debug(f"Content: {html_content[:200]}...")
            
            # In production, this would use real SMTP:
            # msg = MimeMultipart('alternative')
            # msg['Subject'] = subject
            # msg['From'] = self.smtp_config['username']
            # msg['To'] = to_email
            # 
            # html_part = MIMEText(html_content, 'html')
            # msg.attach(html_part)
            # 
            # with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
            #     if self.smtp_config['use_tls']:
            #         server.starttls()
            #     server.login(self.smtp_config['username'], self.smtp_config['password'])
            #     server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

class WeeklyReportGenerator:
    """Generate comprehensive weekly reports"""
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def generate_user_report(self, user_id: str, user_data: Dict[str, Any]) -> WeeklyReport:
        """Generate weekly report for a specific user"""
        
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # In a real implementation, this would query the database
        # For demo, we'll generate realistic sample data
        
        demo_report_data = self._generate_demo_report_data(user_id, start_date, end_date)
        
        return WeeklyReport(
            user_id=user_id,
            week_start=start_date.strftime('%Y-%m-%d'),
            week_end=end_date.strftime('%Y-%m-%d'),
            **demo_report_data,
            generated_at=datetime.utcnow().isoformat()
        )
    
    def _generate_demo_report_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate realistic demo data for weekly report"""
        import random
        
        # Simulate weekly performance
        total_bets = random.randint(8, 25)
        wins = random.randint(int(total_bets * 0.45), int(total_bets * 0.75))
        win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
        
        avg_bet_size = random.uniform(50, 200)
        total_wagered = total_bets * avg_bet_size
        total_profit = random.uniform(-total_wagered * 0.3, total_wagered * 0.4)
        roi = (total_profit / total_wagered) * 100 if total_wagered > 0 else 0
        
        strategies = ['Conservative Strategy', 'Value Hunter', 'ML-Powered Strategy', 'Arbitrage Strategy']
        best_strategy = random.choice(strategies)
        worst_strategy = random.choice([s for s in strategies if s != best_strategy])
        
        # Generate top opportunities
        opportunities = [
            {
                'teams': 'Lakers vs Warriors',
                'sport': 'NBA',
                'confidence': random.randint(65, 85),
                'expected_value': random.uniform(3.5, 12.0)
            },
            {
                'teams': 'Chiefs vs Bills', 
                'sport': 'NFL',
                'confidence': random.randint(70, 90),
                'expected_value': random.uniform(2.8, 8.5)
            },
            {
                'teams': 'Yankees vs Red Sox',
                'sport': 'MLB', 
                'confidence': random.randint(60, 80),
                'expected_value': random.uniform(4.2, 9.1)
            }
        ]
        
        # Generate recommendations based on performance
        recommendations = []
        if win_rate < 55:
            recommendations.append("Consider increasing your confidence threshold to 70%+")
            recommendations.append("Review your bankroll management strategy")
        
        if roi < 5:
            recommendations.append("Focus on higher value opportunities with 5%+ expected value")
        
        if total_bets < 10:
            recommendations.append("Increase betting frequency to capture more opportunities")
        elif total_bets > 20:
            recommendations.append("Consider reducing bet frequency and focusing on quality")
        
        if not recommendations:
            recommendations = [
                "Great performance this week! Keep up the good work.",
                "Consider diversifying across more sports for better risk management."
            ]
        
        # Model performance summary
        model_performance = {
            'nba_model_accuracy': random.uniform(65, 75),
            'nfl_model_accuracy': random.uniform(60, 70),
            'total_predictions': random.randint(15, 30),
            'model_profit_contribution': random.uniform(0.6, 0.9)
        }
        
        # Risk analysis
        risk_analysis = {
            'current_drawdown': random.uniform(0, 15),
            'max_bet_size_pct': random.uniform(2, 5),
            'risk_score': random.randint(3, 8),  # 1-10 scale
            'diversification_score': random.uniform(0.6, 0.9)
        }
        
        return {
            'total_bets': total_bets,
            'total_profit': round(total_profit, 2),
            'win_rate': round(win_rate, 1),
            'roi': round(roi, 1),
            'best_strategy': best_strategy,
            'worst_strategy': worst_strategy,
            'top_opportunities': opportunities,
            'model_performance': model_performance,
            'recommendations': recommendations,
            'risk_analysis': risk_analysis
        }

class UserEngagementSystem:
    """Comprehensive user engagement and retention system"""
    
    def __init__(self):
        self.report_generator = WeeklyReportGenerator()
        self.notification_service = NotificationService()
        self.user_preferences = {}  # In production, load from database
    
    def register_user_preferences(self, user_id: str, email: str, preferences: Dict[str, Any] = None) -> UserPreferences:
        """Register or update user preferences"""
        user_prefs = UserPreferences(
            user_id=user_id,
            email=email,
            **(preferences or {})
        )
        
        self.user_preferences[user_id] = user_prefs
        logger.info(f"Registered preferences for user {user_id}")
        
        return user_prefs
    
    def send_weekly_reports(self, target_day: str = None) -> Dict[str, Any]:
        """Send weekly reports to all eligible users"""
        target_day = target_day or datetime.now().strftime('%A')
        
        sent_count = 0
        failed_count = 0
        
        for user_id, prefs in self.user_preferences.items():
            if prefs.weekly_report_enabled and prefs.preferred_day == target_day:
                try:
                    # Generate report
                    report = self.report_generator.generate_user_report(user_id, {})
                    
                    # Send report
                    success = self.notification_service.send_weekly_report(prefs, report)
                    
                    if success:
                        sent_count += 1
                        logger.info(f"Weekly report sent to user {user_id}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to send weekly report to user {user_id}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error generating/sending report for user {user_id}: {e}")
        
        return {
            'sent_count': sent_count,
            'failed_count': failed_count,
            'target_day': target_day,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def check_performance_alerts(self) -> Dict[str, Any]:
        """Check for performance issues and send alerts"""
        alerts_sent = 0
        
        for user_id, prefs in self.user_preferences.items():
            if prefs.performance_alerts_enabled:
                # In real implementation, check user's actual performance data
                # For demo, simulate some alerts
                
                if user_id.endswith('1'):  # Demo: alert for some users
                    alert_msg = "Your win rate has dropped below 50% in the last 5 bets"
                    recommendation = "Consider adjusting your confidence threshold or reviewing your strategy"
                    
                    success = self.notification_service.send_performance_alert(prefs, alert_msg, recommendation)
                    if success:
                        alerts_sent += 1
        
        return {
            'alerts_sent': alerts_sent,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def notify_model_updates(self, model_name: str, new_accuracy: float, improvement: float) -> Dict[str, Any]:
        """Notify users about model updates"""
        notifications_sent = 0
        
        for user_id, prefs in self.user_preferences.items():
            if prefs.model_updates_enabled:
                success = self.notification_service.send_model_update_notification(
                    prefs, model_name, new_accuracy, improvement
                )
                if success:
                    notifications_sent += 1
        
        return {
            'notifications_sent': notifications_sent,
            'model_name': model_name,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_engagement_analytics(self) -> Dict[str, Any]:
        """Get user engagement analytics"""
        total_users = len(self.user_preferences)
        
        weekly_enabled = sum(1 for prefs in self.user_preferences.values() if prefs.weekly_report_enabled)
        alerts_enabled = sum(1 for prefs in self.user_preferences.values() if prefs.performance_alerts_enabled)
        
        return {
            'total_users': total_users,
            'weekly_reports_enabled': weekly_enabled,
            'performance_alerts_enabled': alerts_enabled,
            'engagement_rate': (weekly_enabled / total_users) * 100 if total_users > 0 else 0,
            'generated_at': datetime.utcnow().isoformat()
        }

# Global engagement system instance
engagement_system = UserEngagementSystem()