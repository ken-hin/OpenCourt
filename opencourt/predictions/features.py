#Import necessary libraries
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from opencourt.models import TeamSeasonStats
import pandas as pd
import numpy as np

"""
As descirbed in the notebook, the following features that will need to be calculated are as follows:

features = [
    'diff_efg_pct',
    'diff_turnover_rate',
    'diff_point_diff',
    'diff_pace',
    'diff_avg_ftr',
    'diff_avg_rating',
    'diff_avg_blocks',
    'diff_avg_oreb_pct',
    'diff_avg_ato_rto',
    'home_advantage',
]

"""



""" For testing
Team_a.off_eff_fg_pct = 1
Team_a.off_turnovers = 1
Team_a.off_possessions = 1
Team_a.off_points = 1
Team_a.opp_points = 1
Team_a.pace = 1
Team_a.off_ft_rate = 1
Team_a.off_rating = 1
Team_a.off_blocks = 1
Team_a.off_oreb_pct = 1
Team_a.off_assists = 1

Team_b.off_eff_fg_pct = 1
Team_b.off_turnovers = 1
Team_b.off_possessions = 1
Team_b.off_points = 1
Team_b.opp_points = 1
Team_b.pace = 1
Team_b.off_ft_rate = 1
Team_b.off_rating = 1
Team_b.off_blocks = 1
Team_b.off_oreb_pct = 1
Team_b.off_assists = 1
"""

def build_features(team_a, team_b, home_advantage):

    # Take in the TeamSeasonStats and build the pandas dataframe from it
    diff_efg_pct = team_a.off_eff_fg_pct - team_b.off_eff_fg_pct
    diff_turnover_rate = (team_a.off_turnovers / team_a.off_possessions) -  (team_b.off_turnovers / team_b.off_possessions)
    diff_point_diff = (team_a.off_points - team_a.opp_points) - (team_b.off_points - team_b.opp_points)
    diff_pace = team_a.pace - team_b.pace
    diff_avg_ftr = team_a.off_ft_rate - team_b.off_ft_rate
    diff_avg_rating = team_a.off_rating - team_b.off_rating
    diff_avg_blocks = team_a.off_blocks - team_b.off_blocks
    diff_avg_oreb_pct = team_a.off_oreb_pct - team_b.off_oreb_pct
    diff_avg_ato_rto = (team_a.off_assists / team_a.off_turnovers) -  (team_b.off_assists / team_b.off_turnovers)

    features = {
    'diff_efg_pct': [diff_efg_pct],
    'diff_turnover_rate': [diff_turnover_rate],
    'diff_point_diff': [diff_point_diff], 
    'diff_pace': [diff_pace],
    'diff_avg_ftr': [diff_avg_ftr],
    'diff_avg_rating': [diff_avg_rating],
    'diff_avg_blocks': [diff_avg_blocks], 
    'diff_avg_oreb_pct': [diff_avg_oreb_pct], 
    'diff_avg_ato_rto': [diff_avg_ato_rto], 
    'home_advantage': [home_advantage]
    }

    final_data = pd.DataFrame(features)
    
    return final_data

