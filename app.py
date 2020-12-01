import pandas as pd
import requests
import io
import json
import sys
import numpy as np

import plotly.express as px
import plotly.graph_objects as go

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import datetime
from dash.dependencies import Input, Output

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__,
                title='Datos COVID19',
                update_title='Cargando...',
                external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions'] = True

server = app.server


url = 'https://coronavirus.sergas.gal/datos/libs/hot-config/hot-config.txt'

s = requests.get(url).content
j = json.loads(s)
for a_source in j['DATA_SOURCE']['FILES']:
    print(a_source['URL'])

# xenero_url = "https://coronavirus.sergas.gal/infodatos/2020-11-26_COVID19_Web_PorcentajeInfectadosPorGenero.csv"
# s_xenero = requests.get(xenero_url).content
#
# df_xenero = pd.read_csv(io.StringIO(s_xenero.decode('utf-8')))
# print(df_xenero.columns)
# print(df_xenero)

df_totais = pd.DataFrame()
today = datetime.date.today()
tomorrow = today+datetime.timedelta(1)
yesterday = today-datetime.timedelta(1)

for day in pd.date_range(start='2020-10-07', end=today):
    totais_url = f"https://coronavirus.sergas.gal/infodatos/{str(day).split()[0]}_COVID19_Web_CifrasTotais.csv"
    #print(totais_url)
    response = requests.get(totais_url)
    if response.status_code == requests.codes.ok:  # i.e status = 200
        content = response.content
        df_diario = pd.read_csv(io.StringIO(content.decode('utf-8')), thousands='.', decimal=',')
        df_totais = pd.concat([df_totais, df_diario], ignore_index=True)
    else:
        print(f'Content for {day} not available. Status code: {response.status_code}')

df_totais[['Casos_Totais',
           'Casos_Confirmados_PCR_Ultimas24h',
           'Pacientes_Sin_Alta',
           'Pacientes_Con_Alta',
           'Camas_Ocupadas_HOS',
           'Camas_Ocupadas_UCI',
           'Probas_Realizadas_PCR',
           'Probas_Realizadas_Non_PCR',
           'Exitus']] = \
    df_totais[['Casos_Totais',
               'Casos_Confirmados_PCR_Ultimas24h',
               'Pacientes_Sin_Alta',
               'Pacientes_Con_Alta',
               'Camas_Ocupadas_HOS',
               'Camas_Ocupadas_UCI',
               'Probas_Realizadas_PCR',
               'Probas_Realizadas_Non_PCR',
               'Exitus']].apply(pd.to_numeric)
df_totais[['Fecha']] = df_totais[['Fecha']].apply(pd.to_datetime)

# change axis for better repreentation

df_totais.set_axis(['Fecha',
                    'Área Sanitaria',
                    'Contaxiados',
                    'Casos confirmados por PCR nas últimas 24 horas',
                    'Pacientes con infección activa',
                    'Curados',
                    'Hospitalizados hoxe',
                    'Coidados intensivos hoxe',
                    'Probas PCR realizadas',
                    'Probas serolóxicas realizadas',
                    'Falecidos'], axis=1, inplace=True)

df_totais['Data'] = pd.to_datetime(df_totais['Fecha']).dt.date

df_totais_extended = pd.concat([
    df_totais, df_totais[
        ['Casos confirmados por PCR nas últimas 24 horas',
         'Falecidos',
         'Curados',
         'Probas PCR realizadas']
    ].diff(periods=8).rename({
        'Casos confirmados por PCR nas últimas 24 horas': 'Diff Casos confirmados por PCR nas últimas 24 horas',
        'Falecidos': 'Diff Falecidos',
        'Curados': 'Diff Curados',
        'Probas PCR realizadas': 'Diff Probas PCR realizadas'
    },
        axis=1)],
    axis=1)

# Calculate 1 and 2 weeks running mean grouped by Área Sanitaria
df_totais_extended['Media 7 días'] = df_totais_extended.groupby('Área Sanitaria')['Casos confirmados por PCR nas últimas 24 horas'].rolling(window=7).mean().reset_index(0,drop=True)
df_totais_extended['Media 14 días'] = df_totais_extended.groupby('Área Sanitaria')['Casos confirmados por PCR nas últimas 24 horas'].rolling(14).mean().reset_index(0, drop=True)

e_date = max(df_totais['Data'])
s_date = e_date - datetime.timedelta(6)
ano = datetime.date.today().year
copyleft = u"\U0001F12F"

app.layout = html.Div(children=[
    html.Img(src=app.get_asset_url('iconfinder-coronavirus-microscope-virus-laboratory-64.png'),
             className='one columns'),
    html.H1('Datos Coronavirus Sergas',
            className='eleven columns',
            ),
    html.Div([
        html.P("Indicador:", className='two columns'),
        dcc.Dropdown(id='dropdown-parameter',
                     options=[
                         {'label': 'Pacientes con infección activa',
                          'value': 'Pacientes con infección activa'},
                         {'label': 'Casos confirmados por PCR nas últimas 24 horas',
                          'value': 'Casos confirmados por PCR nas últimas 24 horas'},
                         {'label': 'Hospitalizados hoxe',
                          'value': 'Hospitalizados hoxe'},
                         {'label': 'Falecidos',
                          'value': 'Falecidos'},
                         {'label': 'Contaxiados',
                          'value': 'Contaxiados'},
                         {'label': 'Curados',
                          'value': 'Curados'},
                         {'label': 'Probas PCR realizadas',
                          'value': 'Probas PCR realizadas'},
                         {'label': 'Probas serolóxicas realizadas',
                          'value': 'Probas serolóxicas realizadas'},
                         {'label': 'Coidados intensivos hoxe',
                          'value': 'Coidados intensivos hoxe'},
                         {'label': 'Diferenza de casos confirmados por PCR nas últimas 24 horas',
                          'value': 'Diff Casos confirmados por PCR nas últimas 24 horas'},
                         {'label': 'Diferenza de probas PCR realizadas con respecto ao día anterior',
                          'value': 'Diff Probas PCR realizadas'},
                         {'label': 'Diferenza de curados con respecto ao día anterior',
                          'value': 'Diff Curados'},
                         {'label': 'Diferenza de falecidos con respecto ao día anterior',
                          'value': 'Diff Falecidos'}
                     ],
                     value='Casos confirmados por PCR nas últimas 24 horas',
                     clearable=False,
                     className='ten columns'
                     )],
    ),
    html.Div([
        html.P("Datas:", className='two columns'),
        dcc.DatePickerRange(
            id='date-picker',
            start_date=s_date,
            end_date=e_date,
            display_format='D-M-Y',
            className='ten columns',
            first_day_of_week=1,
            min_date_allowed='2020-10-07'
        )
    ]),
    html.Div([
        html.P("Área Sanitaria:", className='two columns'),
        dcc.Dropdown(id='dropdown-area',
                     options=[{'label': 'Galicia',
                               'value': 'GALICIA'},
                              {'label': 'A Coruña',
                               'value': 'A.S. A CORUÑA E CEE'},
                              {'label': 'Lugo',
                               'value': 'A.S. LUGO, A MARIÑA E MONFORTE'},
                              {'label': 'Ourense',
                               'value': 'A.S. OURENSE, VERÍN E O BARCO'},
                              {'label': 'Pontevedra',
                               'value': 'A.S. PONTEVEDRA E O SALNÉS'},
                              {'label': 'Vigo',
                               'value': 'A.S. VIGO'},
                              {'label': 'Santiago',
                               'value': 'A.S. SANTIAGO E BARBANZA'},
                              {'label': 'Ferrol',
                               'value': 'A.S. FERROL'}
                              ],
                     value=['GALICIA',
                            'A.S. A CORUÑA E CEE',
                            'A.S. LUGO, A MARIÑA E MONFORTE',
                            'A.S. OURENSE, VERÍN E O BARCO',
                            'A.S. PONTEVEDRA E O SALNÉS',
                            'A.S. VIGO',
                            'A.S. SANTIAGO E BARBANZA',
                            'A.S. FERROL'],
                     multi=True,
                     clearable=False,
                     className='ten columns')
    ]),
    html.Div([
        html.P("Disposición:", className='two columns'),
        dcc.RadioItems(
            id='radio-buttons',
            options=[
                {'label': 'Agrupado', 'value': 'group'},
                {'label': 'Apilado', 'value': 'stack'}
            ],
            value='group',
            labelStyle={'display': 'inline-block'},
            className='ten columns'),
    ]),
    html.Hr(className='twelve columns'),
    html.Div(dcc.Graph(id='main-graph'), className='twelve columns'),
    html.Div(dcc.Graph(id='mean7-graph'), className='twelve columns'),
    html.Div(dcc.Graph(id='mean14-graph'), className='twelve columns'),
    html.Div([html.I(className='fab fa-creative-commons'),
              html.I(className='fab fa-creative-commons-by'),
              html.I(className='far fa-copyright fa-rotate-180'),
              f" {ano} ", html.A("anuf",
                                 href="https://github.com/anuf",
                                 target="_blank"),
              " Todos os dereitos garantidos."],
             style={'textAlign': 'center',
                    'background': 'black',
                    'color': 'white'},
             className='twelve columns'
    )
])


@app.callback(
    [Output('main-graph', 'figure'),
     Output('mean7-graph', 'figure'),
     Output('mean14-graph', 'figure')],
    [Input('dropdown-parameter', 'value'),
     Input('date-picker', 'start_date'), Input('date-picker', 'end_date'),
     Input('radio-buttons', 'value'),
     Input('dropdown-area', 'value')
     ])
def update_figure(dd_parameter, start_date, end_date, rb_value, dd_area):
    if len(dd_area) > 0:
        s_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        e_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()  # datetime.date().fromisoformat(start_date)

        df_to_figure = df_totais_extended[df_totais_extended.Data.between(s_date, e_date)]

        df_to_figure = df_to_figure[df_to_figure['Área Sanitaria'].isin(dd_area)]

        fig_to_update = px.bar(df_to_figure,
                               x='Data',
                               y=dd_parameter,
                               text=dd_parameter,
                               title=dd_parameter,
                               barmode=rb_value,
                               color="Área Sanitaria")

        fig_to_update.update_xaxes(
            dtick=86400000.0,
            tickformat="%d %b",
            ticklabelmode="instant",
            title_text='Data'
        )
        fig_to_update.update_layout(title_x=0.5, yaxis={'title': ''})

        # fig_to_update = go.Figure()
        # fig_to_update.add_trace(go.Scatter(x=df_to_figure['Data'],
        #                                    y=df_to_figure[dd_parameter],
        #                                    mode='lines',
        #                                    name='lines'))
        # fig_to_update.add_trace(go.Bar(x=df_to_figure['Data'],
        #                                y=df_to_figure[dd_parameter],
        #                                name=dd_parameter))

    else:
        fig_to_update = {}

    if dd_parameter == 'Casos confirmados por PCR nas últimas 24 horas':
        fig_mean7_to_update = px.bar(df_to_figure,
                               x='Data',
                               y='Media 7 días',
                               text='Media 7 días',
                               title='Media Casos confirmados por PCR (7 días)',
                               barmode=rb_value,
                               color="Área Sanitaria")
        fig_mean7_to_update.update_xaxes(
            dtick=86400000.0,
            tickformat="%d %b",
            ticklabelmode="instant",
            title_text='Data'
        )
        fig_mean7_to_update.update_traces(texttemplate='%{text:.2f}')
        fig_mean7_to_update.update_layout(title_x=0.5, yaxis={'title': ''})

        fig_mean14_to_update = px.bar(df_to_figure,
                                     x='Data',
                                     y='Media 14 días',
                                     text='Media 14 días',
                                     title='Media Casos confirmados por PCR (14 días)',
                                     barmode=rb_value,
                                     color="Área Sanitaria")
        fig_mean14_to_update.update_xaxes(
            dtick=86400000.0,
            tickformat="%d %b",
            ticklabelmode="instant",
            title_text='Data'
        )
        fig_mean14_to_update.update_traces(texttemplate='%{text:.2f}')
        fig_mean14_to_update.update_layout(title_x=0.5, yaxis={'title': ''})
    else:
        fig_mean7_to_update = {}
        fig_mean14_to_update = {}
    return fig_to_update, fig_mean7_to_update, fig_mean14_to_update


if __name__ == '__main__':
    app.run_server(debug=True)