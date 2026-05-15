import json
import pandas as pd

from scraper.response.response_handler import ResponseHandler
from requests import Response


class FootballResponseHandler(ResponseHandler):
    """Custom response handler that transforms API response to football_data table schema."""

    def handle(self, response: Response) -> pd.DataFrame:

        data = json.loads(response.text)

        if self.data_path:
            for path in self.data_path.split('.'):
                data = data[path]

        df = pd.json_normalize(data)
        
        # Map flattened columns to table schema
        df_mapped = pd.DataFrame()

        df_mapped['match_id'] = df.get('id')
        df_mapped['utc_date'] = df.get('utcDate')
        df_mapped['status'] = df.get('status')
        df_mapped['competition_id'] = df.get('competition.id')
        df_mapped['competition_name'] = df.get('competition.name')
        df_mapped['home_team_id'] = df.get('homeTeam.id')
        df_mapped['home_team'] = df.get('homeTeam.name')
        df_mapped['away_team_id'] = df.get('awayTeam.id')
        df_mapped['away_team'] = df.get('awayTeam.name')
        df_mapped['winner'] = df.get('score.winner')
        df_mapped['home_goals'] = df.get('score.fullTime.home')
        df_mapped['away_goals'] = df.get('score.fullTime.away')
        df_mapped['last_updated'] = df.get('lastUpdated')
        
        return df_mapped
