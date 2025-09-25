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