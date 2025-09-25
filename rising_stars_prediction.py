# rising_stars_prediction.py
import discord
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger('discord')

class RisingStarsPrediction:
    """Module for predicting Rising Stars potential and peak positions"""
    
    # Daily growth benchmarks from documentation (Day -7 to Day 0)
    GROWTH_BENCHMARKS = {
        'position_1': {
            'day_7_6': (16, 25),
            'day_6_5': (35, 45),
            'day_5_4': (44, 100),
            'day_4_3': (66, 122),
            'day_3_2': (97, 124),
            'day_2_1': (91, 127),
            'day_1_0': (204, 255),
            'cumulative': (553, 798)
        },
        'position_2_3': {
            'day_7_6': (10, 17),
            'day_6_5': (14, 25),
            'day_5_4': (28, 51),
            'day_4_3': (36, 74),
            'day_3_2': (56, 74),
            'day_2_1': (61, 72),
            'day_1_0': (93, 154),
            'cumulative': (298, 467)
        },
        'position_4_5': {
            'day_7_6': (10, 14),
            'day_6_5': (12, 19),
            'day_5_4': (17, 40),
            'day_4_3': (35, 49),
            'day_3_2': (37, 67),
            'day_2_1': (49, 70),
            'day_1_0': (72, 115),
            'cumulative': (232, 374)
        },
        'position_6_7': {
            'day_7_6': (8, 12),
            'day_6_5': (10, 14),
            'day_5_4': (12, 58),
            'day_4_3': (32, 59),
            'day_3_2': (14, 59),
            'day_2_1': (32, 87),
            'day_1_0': (56, 94),
            'cumulative': (164, 383)
        },
        'position_8_10': {
            'day_7_6': (7, 10),
            'day_6_5': (8, 12),
            'day_5_4': (19, 35),
            'day_4_3': (22, 55),
            'day_3_2': (30, 63),
            'day_2_1': (19, 53),
            'day_1_0': (45, 57),
            'cumulative': (150, 285)
        }
    }
    
    # Niche tags for better shoutout matching (less popular tags)
    NICHE_TAGS = [
        'strategy', 'war_and_military', 'mythos', 'urban_fantasy', 'non_human_lead',
        'martial_arts', 'grimdark', 'secret_identity', 'low_fantasy', 'attractive_lead',
        'soft_sci_fi', 'tragedy', 'dungeon', 'gamelit', 'dystopia', 'post_apocalyptic',
        'horror', 'ruling_class', 'school_life', 'artificial_intelligence',
        'technologically_engineered', 'time_travel', 'short_story', 'harem',
        'genetically_engineered', 'xianxia', 'super_heroes', 'first_contact',
        'contemporary', 'historical', 'villainous_lead', 'cyberpunk', 'hard_sci_fi',
        'space_opera', 'time_loop', 'virtual_reality', 'gender_bender', 'satire',
        'steampunk', 'wuxia', 'reader_interactive', 'sports'
    ]
    
    def __init__(self, wpdb, book_id: int, book_data: Dict, snapshots: List[Dict]):
        self.wpdb = wpdb
        self.book_id = book_id  # Internal database ID
        self.book_data = book_data
        self.snapshots = snapshots
        self.daily_growth = self.calculate_daily_growth()
        
    def calculate_daily_growth(self) -> List[Tuple[datetime, int]]:
        """Calculate daily follower growth from snapshots"""
        if len(self.snapshots) < 2:
            return []
        
        daily_growth = []
        for i in range(1, len(self.snapshots)):
            date = datetime.strptime(self.snapshots[i]['timestamp'], '%Y-%m-%d %H:%M:%S')
            prev_followers = int(self.snapshots[i-1]['followers'])
            curr_followers = int(self.snapshots[i]['followers'])
            growth = curr_followers - prev_followers
            daily_growth.append((date, growth))
            
        return daily_growth
    
    def check_eligibility(self) -> Tuple[bool, str]:
        """Check if book is eligible for Rising Stars prediction"""
        
        # Check 1: Book should NOT have appeared on main RS before
        has_main_rs = self.wpdb.get_var(self.wpdb.prepare("""
            SELECT COUNT(*) FROM {self.wpdb.prefix}rr_genre_rising_stars
            WHERE book_id = %d AND rs_tag = 'main'
        """, self.book_id))
        
        if has_main_rs > 0:
            return False, "Book has already appeared on Main Rising Stars"
        
        # Check 2: Book should NOT have records before 2025-07-01
        old_records = self.wpdb.get_var(self.wpdb.prepare("""
            SELECT COUNT(*) FROM {self.wpdb.prefix}rr_book_snapshot
            WHERE book_id = %d AND DATE(timestamp) < '2025-07-01'
        """, self.book_id))
        
        if old_records > 0:
            return False, "Book has tracking data before July 2025"
        
        # Check 3: If book has records older than 1 month, followers shouldn't be > 200
        one_month_ago = datetime.now() - timedelta(days=30)
        old_high_followers = self.wpdb.get_var(self.wpdb.prepare("""
            SELECT MAX(followers) FROM {self.wpdb.prefix}rr_book_snapshot
            WHERE book_id = %d AND DATE(timestamp) < %s
        """, self.book_id, one_month_ago.strftime('%Y-%m-%d')))
        
        if old_high_followers and int(old_high_followers) > 200:
            return False, "Book has too many followers for its age"
        
        # Check 4: Daily growth shouldn't be < 3 for at least 2 days
        recent_growth = self.daily_growth[-7:] if len(self.daily_growth) >= 7 else self.daily_growth
        low_growth_days = sum(1 for _, growth in recent_growth if growth < 3)
        
        if len(recent_growth) >= 2 and low_growth_days >= len(recent_growth) - 1:
            return False, "Insufficient daily growth (need 3+ followers/day)"
        
        # Check 5: Book must appear on at least one genre RS list
        has_genre_rs = self.wpdb.get_var(self.wpdb.prepare("""
            SELECT COUNT(DISTINCT rs_tag) FROM {self.wpdb.prefix}rr_genre_rising_stars
            WHERE book_id = %d AND rs_tag != 'main'
        """, self.book_id))
        
        if has_genre_rs == 0:
            return False, "Book has not appeared on any genre Rising Stars lists"
        
        return True, "Eligible for Rising Stars prediction"
    
def add_detailed_rs_prediction(embed: discord.Embed, rs_data: Dict) -> discord.Embed:
    """
    Add detailed Rising Stars prediction information to an embed
    """
    if not rs_data.get('eligible'):
        return embed
    
    is_premium = rs_data.get('is_premium', False)
    
    # Add separator
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━",
        value="**🌟 RISING STARS ANALYSIS 🌟**",
        inline=False
    )
    
    if not is_premium:
        # Free tier - basic information
        embed = add_free_tier_rs_info(embed, rs_data)
    else:
        # Premium tier - detailed analysis
        embed = add_premium_tier_rs_info(embed, rs_data)
    
    return embed


def add_free_tier_rs_info(embed: discord.Embed, rs_data: Dict) -> discord.Embed:
    """
    Add free tier RS information to embed
    """
    growth_metrics = rs_data.get('growth_metrics', {})
    recent_avg = growth_metrics.get('recent_avg_growth', 0)
    
    # Basic growth assessment
    if recent_avg >= 10:
        growth_status = "✅ **Strong growth detected!**"
        urgency = "Your book may reach Rising Stars soon."
    elif recent_avg >= 5:
        growth_status = "📈 **Moderate growth detected**"
        urgency = "With marketing boost, RS is achievable within 1-2 weeks."
    else:
        growth_status = "🌱 **Building momentum**"
        urgency = "Focus on growth - need 10+ followers/day for RS potential."
    
    embed.add_field(
        name="📊 Growth Status",
        value=f"{growth_status}\nCurrent: {recent_avg:.1f} followers/day\n{urgency}",
        inline=False
    )
    
    # Action items for free users
    embed.add_field(
        name="💡 Immediate Action Items",
        value=(
            "**1.** 🤝 Reach out to shoutout partners NOW\n"
            "   • Similar books in your genre\n"
            "   • 2-3 days notice needed\n\n"
            "**2.** 💰 Consider scheduling ads\n"
            "   • 2-3 days approval time\n"
            "   • Budget $10-30 per ad\n\n"
            "**3.** 📅 Post consistently\n"
            "   • Peak times: 6-9 PM EST\n"
            "   • Weekend releases get more views"
        ),
        inline=False
    )
    
    # Risk disclaimer
    embed.add_field(
        name="⚠️ Important Disclaimer",
        value=(
            "*Ads are a financial risk with no guaranteed returns. "
            "This analysis is not financial advice. "
            "Success depends on many factors including content quality, "
            "timing, and reader engagement.*"
        ),
        inline=False
    )
    
    # Upgrade prompt
    embed.add_field(
        name="🔓 Unlock Full Analysis",
        value=(
            "**Premium features include:**\n"
            "• 🎯 Peak position predictions (Top 3/7/25)\n"
            "• 📈 Probability percentages for each tier\n"
            "• 📊 Required views/followers calculations\n"
            "• 🎨 Customized marketing timeline\n"
            "• 🔍 Niche-matched shoutout partner finder\n"
            "• ⏰ Specific timeline estimates\n\n"
            "**[Support on Patreon](https://www.patreon.com/stepanchizhov)**"
        ),
        inline=False
    )
    
    return embed

    def add_premium_tier_rs_info(embed: discord.Embed, rs_data: Dict) -> discord.Embed:
        """
        Add premium tier detailed RS analysis to embed
        """
        growth_metrics = rs_data.get('growth_metrics', {})
        predictions = rs_data.get('predictions', {})
        enhanced = rs_data.get('enhanced_predictions', {})
        trajectory = rs_data.get('growth_trajectory', {})
        
        # Current metrics with trajectory
        metrics_text = (
            f"**Daily Average:** {growth_metrics.get('recent_avg_growth', 0):.1f} followers/day\n"
            f"**Weekly Total:** {growth_metrics.get('week_growth', 0)} followers\n"
            f"**Current Base:** {growth_metrics.get('current_followers', 0):,} followers"
        )
        
        if trajectory:
            metrics_text += f"\n\n**Trajectory:** {trajectory.get('pattern', 'Unknown')}"
            metrics_text += f"\n**Trend:** {trajectory.get('trend', 'Unknown')}"
            metrics_text += f"\n**Volatility:** {trajectory.get('volatility', 'Unknown')}"
        
        embed.add_field(
            name="📊 Current Growth Metrics",
            value=metrics_text,
            inline=True
        )
        
        # Position predictions with confidence
        if predictions:
            pred_text = (
                f"**Estimated Peak:** #{predictions.get('estimated_position_range', 'Unknown')}\n"
                f"**Confidence:** {predictions.get('confidence', 'Low').title()}\n"
            )
            
            if enhanced:
                pred_text += f"\n**Growth Phase:** {enhanced.get('growth_phase', 'Unknown')}"
                pred_text += f"\n**Day 0 Estimate:** +{enhanced.get('estimated_day0_growth', 0)} followers"
                
                if 'acceleration_bonus' in enhanced:
                    pred_text += f"\n🚀 {enhanced['acceleration_bonus']}"
                elif 'acceleration_penalty' in enhanced:
                    pred_text += f"\n⚠️ {enhanced['acceleration_penalty']}"
            
            embed.add_field(
                name="🎯 Peak Position Analysis",
                value=pred_text,
                inline=True
            )
        
        # Timeline estimate
        timeline = rs_data.get('estimated_timeline', predictions.get('timeline', 'Unknown'))
        embed.add_field(
            name="⏰ RS Timeline",
            value=f"**{timeline}**",
            inline=True
        )
        
        # Probability breakdown
        if predictions.get('position_probabilities'):
            prob_text = ""
            probs = predictions['position_probabilities']
            
            # Sort by position order
            position_order = ['#1', '#2-3', '#4-5', '#6-7', 'Below #7']
            for pos in position_order:
                if pos in probs and probs[pos] > 0:
                    # Add visual bar
                    bar_length = int(probs[pos] / 10)
                    bar = "█" * bar_length + "░" * (10 - bar_length)
                    prob_text += f"**{pos}:** {bar} {probs[pos]}%\n"
            
            embed.add_field(
                name="📊 Position Probabilities",
                value=prob_text or "No probability data available",
                inline=False
            )
        
        # Required metrics for targets
        required_views = rs_data.get('required_views', {})
        if required_views:
            # Focus on achievable targets based on current growth
            current_avg = growth_metrics.get('recent_avg_growth', 0)
            
            targets_text = ""
            if current_avg < 20:
                # Show Top 25 and Top 7
                for target in ['top_25', 'top_7']:
                    if target in required_views:
                        data = required_views[target]
                        name = "Top 25" if target == 'top_25' else "Top 7"
                        targets_text += f"**{name} Requirements:**\n"
                        targets_text += f"• Views: {data['views_needed']:,}\n"
                        targets_text += f"• Followers: {data['followers_needed']:,}\n\n"
            else:
                # Show Top 7 and Top 3
                for target in ['top_7', 'top_3']:
                    if target in required_views:
                        data = required_views[target]
                        name = "Top 7" if target == 'top_7' else "Top 3"
                        targets_text += f"**{name} Requirements:**\n"
                        targets_text += f"• Views: {data['views_needed']:,}\n"
                        targets_text += f"• Followers: {data['followers_needed']:,}\n\n"
            
            if targets_text:
                embed.add_field(
                    name="📈 Day 0 Target Requirements",
                    value=targets_text.strip(),
                    inline=False
                )
        
        # Specific recommendations
        recommendations = rs_data.get('specific_recommendations', [])
        marketing = rs_data.get('marketing_recommendations', {})
        
        if recommendations:
            # Group by priority
            urgent = [r for r in recommendations if r.get('priority') == 'urgent']
            high = [r for r in recommendations if r.get('priority') == 'high']
            medium = [r for r in recommendations if r.get('priority') == 'medium']
            
            rec_text = ""
            if urgent:
                rec_text += "**🚨 URGENT:**\n"
                for r in urgent[:2]:
                    rec_text += f"{r['text']}\n"
                rec_text += "\n"
            
            if high:
                rec_text += "**⚡ High Priority:**\n"
                for r in high[:2]:
                    rec_text += f"{r['text']}\n"
                rec_text += "\n"
            
            if medium and len(rec_text) < 800:  # Discord limit
                rec_text += "**📝 Also Consider:**\n"
                for r in medium[:2]:
                    rec_text += f"{r['text']}\n"
            
            if rec_text:
                embed.add_field(
                    name="🎯 Personalized Action Plan",
                    value=rec_text.strip(),
                    inline=False
                )
        elif marketing:
            # Use basic marketing recommendations
            current_avg = growth_metrics.get('recent_avg_growth', 0)
            
            # Find the most relevant target
            if current_avg < 15:
                target_data = marketing.get('top_25', {})
                target_name = "Top 25"
            elif current_avg < 30:
                target_data = marketing.get('top_10', {})
                target_name = "Top 10"
            else:
                target_data = marketing.get('top_7', {})
                target_name = "Top 7"
            
            if target_data.get('gap', 0) > 0:
                rec_text = (
                    f"**Target: {target_name}**\n"
                    f"• Need +{target_data['gap']:.0f} followers/day\n"
                    f"• {target_data.get('ads_recommended', 0)} ads recommended\n"
                    f"• {target_data.get('shoutouts_recommended', 0)} shoutouts needed\n"
                    f"• Est. ad budget: {target_data.get('estimated_cost', {}).get('ads', '$10-30')}"
                )
            else:
                rec_text = f"✅ Current growth sufficient for {target_name}!\nMaintain consistency."
            
            embed.add_field(
                name="📋 Marketing Requirements",
                value=rec_text,
                inline=False
            )
        
        # Shoutout partner finder
        search_url = rs_data.get('shoutout_search_url')
        if search_url:
            embed.add_field(
                name="🤝 Find Shoutout Partners",
                value=(
                    f"[**🔍 Search Matching Books**]({search_url})\n"
                    "*Books with similar genres and reader base*\n"
                    "*Sorted by engagement for best matches*"
                ),
                inline=False
            )
        
        # Genre RS performance
        genre_rs = rs_data.get('genre_rs_appearances', [])
        if genre_rs:
            genre_text = "**Current Rankings:**\n"
            for i, appearance in enumerate(genre_rs[:5]):  # Top 5
                tag = appearance['rs_tag'].replace('_', ' ').title()
                genre_text += f"• **{tag}:** #{appearance['best_position']} "
                genre_text += f"({appearance['appearances']}x)\n"
            
            embed.add_field(
                name="🏆 Genre Rising Stars",
                value=genre_text,
                inline=True
            )
        
        # Risk disclaimer (always include)
        embed.add_field(
            name="⚠️ Disclaimer",
            value=(
                "*Marketing involves financial risk. Results not guaranteed. "
                "This is analytical data, not financial advice.*"
            ),
            inline=False
        )
        
        return embed
    
    
    def create_rs_summary_field(rs_data: Dict) -> Optional[Dict]:
        """
        Create a summary field for RS prediction (used in quick checks)
        """
        if not rs_data or not rs_data.get('eligible'):
            return None
        
        growth_metrics = rs_data.get('growth_metrics', {})
        recent_avg = growth_metrics.get('recent_avg_growth', 0)
        
        if recent_avg >= 10:
            icon = "🔥"
            status = "High RS Potential"
        elif recent_avg >= 5:
            icon = "📈"
            status = "Moderate RS Potential"
        else:
            icon = "🌱"
            status = "Building RS Potential"
        
        return {
            'name': f"{icon} Rising Stars Alert",
            'value': f"**{status}** - Use `rs_prediction:True` for full analysis",
            'inline': False
        }
    
    def predict_position(self, week_growth: int, day0_growth: int = None) -> Dict:
        """Predict potential RS position based on growth patterns"""
        
        # If we don't have day0 growth yet, estimate from recent trend
        if day0_growth is None:
            recent_avg = np.mean([g for _, g in self.daily_growth[-3:]]) if len(self.daily_growth) >= 3 else 10
            day0_growth = int(recent_avg * 2.5)  # Assume boost on RS entry
        
        predictions = {
            'position_ranges': [],
            'probabilities': {},
            'confidence': 'low'
        }
        
        # Compare against benchmarks
        if week_growth >= 550 and day0_growth >= 200:
            predictions['position_ranges'].append('1-3')
            predictions['probabilities'] = {
                '1': 15, '2-3': 35, '4-5': 30, '6-7': 15, 'Below 7': 5
            }
            predictions['confidence'] = 'medium-high'
        elif week_growth >= 300 and day0_growth >= 90:
            predictions['position_ranges'].append('2-5')
            predictions['probabilities'] = {
                '1': 5, '2-3': 25, '4-5': 35, '6-7': 25, 'Below 7': 10
            }
            predictions['confidence'] = 'medium'
        elif week_growth >= 230 and day0_growth >= 70:
            predictions['position_ranges'].append('4-7')
            predictions['probabilities'] = {
                '1': 2, '2-3': 10, '4-5': 25, '6-7': 35, 'Below 7': 28
            }
            predictions['confidence'] = 'medium'
        elif week_growth >= 160 and day0_growth >= 55:
            predictions['position_ranges'].append('6-10')
            predictions['probabilities'] = {
                '1': 0, '2-3': 5, '4-5': 15, '6-7': 30, 'Below 7': 50
            }
            predictions['confidence'] = 'low-medium'
        else:
            predictions['position_ranges'].append('8-15')
            predictions['probabilities'] = {
                '1': 0, '2-3': 2, '4-5': 8, '6-7': 20, 'Below 7': 70
            }
            predictions['confidence'] = 'low'
        
        return predictions
    
    def calculate_required_views_for_positions(self) -> Dict:
        """Calculate required views on Day 0 for different position targets"""
        
        # Based on documentation thresholds
        return {
            'top_1': {
                'followers': 1686,
                'views': 74984,
                'chapters': 18,
                'views_per_chapter': 4166
            },
            'top_3': {
                'followers': 1529,
                'views': 67928,
                'chapters': 21,
                'views_per_chapter': 3314
            },
            'top_7': {
                'followers': 1110,
                'views': 50000,
                'chapters': 25,
                'views_per_chapter': 2000
            },
            'top_25': {
                'followers': 500,
                'views': 25000,
                'chapters': 15,
                'views_per_chapter': 1667
            }
        }
    
    def get_marketing_recommendations(self, current_growth: float, target_position: str) -> List[str]:
        """Get marketing recommendations based on current growth and target"""
        
        recommendations = []
        
        # Calculate needed daily growth for target
        target_ranges = {
            'top_3': (50, 100),
            'top_7': (30, 60),
            'top_10': (20, 40),
            'top_25': (10, 25)
        }
        
        if target_position in target_ranges:
            min_needed, max_needed = target_ranges[target_position]
            gap = min_needed - current_growth
            
            if gap > 0:
                # Need more growth
                ads_needed = int(gap / 2)  # Assume 2 followers per ad
                shoutouts_needed = int(gap / 5)  # Assume 5 followers per shoutout
                
                recommendations.append(f"📈 To reach {target_position}, increase daily growth by {gap:.0f} followers/day")
                recommendations.append(f"💰 Consider {ads_needed}-{ads_needed+1} targeted ads (1-3 followers/ad/day)")
                recommendations.append(f"🤝 Schedule {shoutouts_needed}-{shoutouts_needed+2} shoutouts with similar books")
                recommendations.append("⚡ Post chapters at peak reader times (evenings/weekends)")
            else:
                recommendations.append(f"✅ Current growth sufficient for {target_position} potential")
                recommendations.append("🎯 Maintain consistency and quality")
        
        return recommendations
    
    def generate_book_search_url(self, book_genres: List[str]) -> str:
        """Generate search URL for finding shoutout partners"""
        
        # Find niche tags in book's genres
        niche_matches = [tag for tag in book_genres if tag.lower() in self.NICHE_TAGS]
        
        if not niche_matches:
            # Use first 2-3 genres
            niche_matches = book_genres[:3]
        
        # Format tags for URL
        tags_param = "%2C".join(niche_matches)
        
        base_url = "https://stepan.chizhov.com/author-tools/book-search/"
        params = [
            "sort_by=average_views",
            "sort_order=asc",
            f"tags_or={tags_param}",
            "status=ONGOING%2CSTUB",
            "range_average_views_min=1478",
            "range_average_views_max=500000",
            "search=true",
            "search_page=1"
        ]
        
        return f"{base_url}?{'&'.join(params)}"
