import requests
import json
import pandas as pd
import io
import datetime


class DataLoader:

    def __init__(self):
        self.config_url = 'https://coronavirus.sergas.gal/datos/libs/hot-config/hot-config.txt'
        self.data_url = 'https://coronavirus.sergas.gal/infodatos'

    def get_config(self):

        # Configuration url for data at Sergas

        response_content = requests.get(self.config_url).content
        json_content = json.loads(response_content)
        url_list = [a_source['URL'] for a_source in json_content['DATA_SOURCE']['FILES']]
        print("\n".join(url_list))
        return url_list

    def get_new_data(self, df, end_date):

        start_date = '2020-10-07'
        # start_date = '2021-05-25'
        if df.empty:
            unique_data = ''
        else:
            unique_data = [x.split()[0] for x in df['Fecha'].unique()]

        for some_date in pd.date_range(start=start_date, end=end_date):
            a_date = str(some_date.date())
            if a_date not in unique_data:
                print(f"Non-existent: {a_date} data in DF. Trying to add it ...")
                daily_url = f"{self.data_url}/{a_date}_COVID19_Web_CifrasTotais.csv"
                response = requests.get(daily_url)

                if response.status_code == requests.codes.ok:  # i.e status = 200
                    daily_df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), thousands='.', decimal=',')
                    df = pd.concat([df, daily_df], ignore_index=True)
                elif response.status_code == requests.codes.not_found:  # i.e status = 404
                    print(
                        f'Content for {a_date}_COVID19_Web_CifrasTotais.csv not available. Status code: {response.status_code}')

                    daily_url = f"{self.data_url}/{a_date}_COVID19_Web_CifrasTotais_PDIA.csv"
                    response = requests.get(daily_url)
                    if response.status_code == requests.codes.ok:  # i.e status = 200
                        daily_df_pdia = pd.read_csv(io.StringIO(response.content.decode('utf-8')), thousands='.',
                                               decimal=',')
                        # remove last column
                        del daily_df_pdia['Probas_Antixenos_Realizadas']
                        # rename
                        daily_df_pdia.rename(columns={
                            'Probas_Realizadas_Non_PDIA': 'Probas_Realizadas_Non_PCR',
                            'Casos_Confirmados_PDIA_Ultimas24h': 'Casos_Confirmados_PCR_Ultimas24h'
                        },
                            inplace=True)

                        df = pd.concat([df, daily_df_pdia], ignore_index=True)
                    else:
                        print(f'Content for {a_date}_COVID19_Web_CifrasTotais_PDIA.csv not available. Status code: {response.status_code}')
                else:
                    print(f'Content for {a_date} not available. Status code: {response.status_code}')

            else:
                pass

        df.to_csv('total_data.csv', index=False)

    def get_activos_curados_falecidos(self, a_day):
        yesterday = a_day-datetime.timedelta(1)
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        activos_curados_falecidos_url = f"{self.data_url}/{yesterday_str}_COVID19_Web_ActivosCuradosFallecidos.csv"
        response = requests.get(activos_curados_falecidos_url)

        if response.status_code == requests.codes.ok:  # i.e status = 200
            activos_curados_falecidos_df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), thousands='.',
                                                       decimal=',')

            activos_curados_falecidos_df.to_csv('activos_curados_falecidos.csv', index=False)
            print('GOT activos_curados_falecidos')
        else:
            print('Unable to get activos_curados_falecidos')


if __name__ == '__main__':

    today = datetime.date.today()
    try:
        main_df = pd.read_csv('total_data.csv')
    except Exception as e:
        print(f"Exception {e.__cause__}")
        main_df = pd.DataFrame()
    loader = DataLoader()
    loader.get_config()
    loader.get_new_data(main_df, today)
    loader.get_activos_curados_falecidos(today)
