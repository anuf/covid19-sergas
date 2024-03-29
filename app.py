import time

import pandas as pd
import requests
import io
import json

import plotly.express as px

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html

import datetime
from dash.dependencies import Input, Output

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css',
                        'https://use.fontawesome.com/releases/v5.15.1/css/all.css']

NEED_NEW_DATA = False

today = datetime.date.today()
tomorrow = today + datetime.timedelta(1)
yesterday = today - datetime.timedelta(1)
before_yesterday = today - datetime.timedelta(2)
population_galicia_2020 = 2701819

app = dash.Dash(__name__,
                title='Datos COVID19',
                update_title='Cargando...',
                external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions'] = True

server = app.server


def get_new_data(end_date):
    # Configuration url for data at Sergas
    config_url = 'https://coronavirus.sergas.gal/datos/libs/hot-config/hot-config.txt'

    response_content = requests.get(config_url).content
    json_content = json.loads(response_content)

    for a_source in json_content['DATA_SOURCE']['FILES']:
        print(a_source['URL'])

    # Main dataframe to join daily data
    main_df_ = pd.DataFrame()

    for day in pd.date_range(start='2020-10-07', end=end_date):
        daily_url = f"https://coronavirus.sergas.gal/infodatos/{str(day).split()[0]}_COVID19_Web_CifrasTotais.csv"
        response = requests.get(daily_url)
        if response.status_code == requests.codes.ok:  # i.e status = 200
            daily_df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), thousands='.', decimal=',')
            main_df_ = pd.concat([main_df_, daily_df], ignore_index=True)
        else:
            print(f'Content for {day} not available. Status code: {response.status_code}')

    main_df_.to_csv('total_data.csv', index=False)


def get_activos_curados_falecidos(a_day):
    yesterday = a_day - datetime.timedelta(1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    activos_curados_falecidos_url = f"https://coronavirus.sergas.gal/infodatos/{yesterday_str}_COVID19_" \
                                    f"Web_ActivosCuradosFallecidos.csv"
    response = requests.get(activos_curados_falecidos_url)

    if response.status_code == requests.codes.ok:  # i.e status = 200
        activos_curados_falecidos_df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), thousands='.',
                                                   decimal=',')

        activos_curados_falecidos_df.to_csv('activos_curados_falecidos.csv', index=False)
        print('GOT activos_curados_falecidos')
    else:
        print('Unable to get activos_curados_falecidos')


if NEED_NEW_DATA:
    get_new_data(today)
    get_activos_curados_falecidos(today)

main_df = pd.read_csv('total_data.csv')
activos_curados_falecidos_df = pd.read_csv('activos_curados_falecidos.csv')

# Type conversion
main_df[['Casos_Totais',
         'Casos_Confirmados_PCR_Ultimas24h',
         'Pacientes_Sin_Alta',
         'Pacientes_Con_Alta',
         'Camas_Ocupadas_HOS',
         'Camas_Ocupadas_UCI',
         'Probas_Realizadas_PCR',
         'Probas_Realizadas_Non_PCR',
         'Exitus']] = \
    main_df[['Casos_Totais',
             'Casos_Confirmados_PCR_Ultimas24h',
             'Pacientes_Sin_Alta',
             'Pacientes_Con_Alta',
             'Camas_Ocupadas_HOS',
             'Camas_Ocupadas_UCI',
             'Probas_Realizadas_PCR',
             'Probas_Realizadas_Non_PCR',
             'Exitus']].apply(pd.to_numeric)
main_df[['Fecha']] = main_df[['Fecha']].apply(pd.to_datetime)

activos_curados_falecidos_df[['Pacientes_Sin_Alta', 'Pacientes_Con_Alta', 'Exitus']] = \
    activos_curados_falecidos_df[['Pacientes_Sin_Alta', 'Pacientes_Con_Alta', 'Exitus']].apply(pd.to_numeric)
activos_curados_falecidos_df[['Fecha']] = activos_curados_falecidos_df[['Fecha']].apply(pd.to_datetime)

# Change column names for nicer representation
main_df.set_axis(['Fecha',
                  'Área Sanitaria',
                  'Contaxiados',
                  'Casos confirmados por PCR nas últimas 24 horas',
                  'Pacientes con infección activa',
                  'Curados',
                  'Hospitalizados hoxe',
                  'Coidados intensivos hoxe',
                  'Probas PCR realizadas',
                  'Probas serolóxicas realizadas',
                  'Falecidos'],
                 axis=1, inplace=True)

activos_curados_falecidos_df.set_axis(['Data',
                                       'Área Sanitaria',
                                       'Pacientes Sen Alta',
                                       'Pacientes Con Alta',
                                       'Exitus'],
                                      axis=1, inplace=True)
# Create date column
main_df['Data'] = pd.to_datetime(main_df['Fecha']).dt.date

# Extend Dataframe with additional calculations
main_df_extended = pd.concat([
    main_df, main_df[
        ['Casos confirmados por PCR nas últimas 24 horas',
         'Falecidos',
         'Curados',
         'Contaxiados',
         'Probas PCR realizadas',
         'Pacientes con infección activa',
         'Probas serolóxicas realizadas']
    ].diff(periods=8).rename({
        'Casos confirmados por PCR nas últimas 24 horas': 'Diff Casos confirmados por PCR nas últimas 24 horas',
        'Falecidos': 'Diff Falecidos',
        'Curados': 'Diff Curados',
        'Contaxiados': 'Diff Contaxiados',
        'Probas PCR realizadas': 'Diff Probas PCR realizadas',
        'Pacientes con infección activa': 'Diff Pacientes con infección activa',
        'Probas serolóxicas realizadas': 'Diff Probas serolóxicas realizadas'
    },
        axis=1)],
    axis=1)

#
main_df_extended['Suma_Hospitalizados_UCI'] = main_df_extended['Hospitalizados hoxe'] + \
                                              main_df_extended['Coidados intensivos hoxe']

main_df_extended['Novos positivos'] = main_df_extended['Diff Pacientes con infección activa'] + \
                                      main_df_extended['Diff Curados'] + \
                                      main_df_extended['Diff Falecidos']
# ----------- Running means
# Calculate 1 and 2 weeks running mean grouped by 'Área Sanitaria'
main_df_extended['Media 7 días'] = \
    main_df_extended.groupby('Área Sanitaria')['Casos confirmados por PCR nas últimas 24 horas'].rolling(
        window=7).mean().reset_index(0, drop=True)
main_df_extended['Media 14 días'] = \
    main_df_extended.groupby('Área Sanitaria')['Casos confirmados por PCR nas últimas 24 horas'].rolling(
        14).mean().reset_index(0, drop=True)

main_df_extended['Media 7 días Casos Activos'] = \
    main_df_extended.groupby('Área Sanitaria')['Pacientes con infección activa'].rolling(
        window=7).mean().reset_index(0, drop=True)
main_df_extended['Media 14 días Casos Activos'] = \
    main_df_extended.groupby('Área Sanitaria')['Pacientes con infección activa'].rolling(
        14).mean().reset_index(0, drop=True)

main_df_extended['Incidencia 7 días Casos Activos'] = \
    main_df_extended.groupby('Área Sanitaria')['Pacientes con infección activa'].rolling(
        window=7).mean().reset_index(0, drop=True)*100000/population_galicia_2020

main_df_extended['Incidencia 14 días Casos Activos'] = \
    main_df_extended.groupby('Área Sanitaria')['Pacientes con infección activa'].rolling(
        14).mean().reset_index(0, drop=True)*100000/population_galicia_2020

main_df_extended['Media 7 días Novos positivos'] = \
    main_df_extended.groupby('Área Sanitaria')['Novos positivos'].rolling(window=7).mean().reset_index(0, drop=True)
main_df_extended['Media 14 días Novos positivos'] = \
    main_df_extended.groupby('Área Sanitaria')['Novos positivos'].rolling(14).mean().reset_index(0, drop=True)

e_date = max(main_df['Data'])
s_date = e_date - datetime.timedelta(6)
today_year = datetime.date.today().year
footer_year = f'2020 - {today_year}' if today_year != 2020 else '2020'

table_df = main_df[['Data', 'Área Sanitaria', 'Contaxiados',
                    'Casos confirmados por PCR nas últimas 24 horas',
                    'Pacientes con infección activa', 'Curados', 'Hospitalizados hoxe',
                    'Coidados intensivos hoxe', 'Probas PCR realizadas',
                    'Probas serolóxicas realizadas', 'Falecidos']]

table_df_transposed = table_df[table_df['Data'] >= before_yesterday]
print(table_df_transposed.shape)
table_df_transposed.set_index(['Data', 'Área Sanitaria'], inplace=True)
print(table_df_transposed.T)
# print(table_df_transposed.columns)
# print(table_df_transposed.index)
# table_df_transposed.set_index('Data', inplace=True)
# print(table_df_transposed.index.names)
max_data = max(table_df['Data'])
print(type(max_data))
print(max_data)
#import sys
#sys.exit(1)
max_data_str = f"{max_data.day}/{max_data.month}/{max_data.year}"

tab_content_table = html.Div([
    dash_table.DataTable(
        id='taboa',
        columns=[{"name": i, "id": i} for i in table_df_transposed.T.columns.names],
        data=table_df_transposed.to_dict('records'),
        sort_action='native',
        filter_action='native'
    )
])
tab_content_table2 = html.Div([
    dash_table.DataTable(
        id='taboa',
        columns=[{"name": i, "id": i} for i in table_df.columns],
        data=table_df[table_df['Data'] >= before_yesterday].to_dict('records'),
        sort_action='native',
        filter_action='native'
    )
])

# The layout
app.layout = html.Div([
    html.Div([
        html.Img(src=app.get_asset_url('iconfinder-coronavirus-microscope-virus-laboratory-64.png')),
        html.H1('Datos Coronavirus Sergas', style={'display': 'inline-block'}),
        html.H6([f'Últimos datos: {max_data_str}. Fonte ',
                 html.A("sergas", href="https://coronavirus.sergas.es/datos/#/gl-ES/galicia"), '/ Elaboración propia'])
    ], style={'verticalAlign': 'middle'}),
    html.Div([
        html.Div([
            html.Label("Indicador:"),
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
                             {'label': 'Diferenza de probas serolóxicas realizadas con respecto ao día anterior',
                              'value': 'Diff Probas serolóxicas realizadas'},
                             {'label': 'Diferenza de Contaxiados con respecto ao día anterior',
                              'value': 'Diff Contaxiados'},
                             {'label': 'Diferenza de curados con respecto ao día anterior',
                              'value': 'Diff Curados'},
                             {'label': 'Diferenza de falecidos con respecto ao día anterior',
                              'value': 'Diff Falecidos'},
                             {'label': 'Diferenza de pacientes con infeción activa con respecto ao día anterior',
                              'value': 'Diff Pacientes con infección activa'},
                             {'label': 'Suma de hospitalizados e UCI',
                              'value': 'Suma_Hospitalizados_UCI'},
                             {'label': 'Novos positivos',
                              'value': 'Novos positivos'}
                         ],
                         value='Casos confirmados por PCR nas últimas 24 horas',
                         clearable=False
                         ),
            html.Label("Área Sanitaria:"),
            dcc.Dropdown(id='dropdown-area',
                         options=[
                             {'label': 'Galicia',
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
                                'A.S. FERROL'
                                ],
                         multi=True,
                         clearable=False),
        ], className='six columns'),
        html.Div([
            html.Label("Datas:"),
            dcc.DatePickerRange(
                id='date-picker',
                start_date=s_date,
                end_date=e_date,
                display_format='D-M-Y',
                # className='ten columns',
                first_day_of_week=1,
                min_date_allowed='2020-10-07',
                max_date_allowed=str(max_data+datetime.timedelta(1))
            ),
            html.Label("Disposición:"),
            dcc.RadioItems(
                id='radio-buttons',
                options=[
                    {'label': 'Agrupada', 'value': 'group'},
                    {'label': 'Apilada', 'value': 'stack'}
                ],
                value='group',
                labelStyle={'display': 'inline-block'}),
        ], className='six columns')
    ]),

    html.Hr(className='twelve columns'),
    html.Div(dcc.Graph(id='main-graph'), className='twelve columns'),
    html.Div(dcc.Graph(id='mean7-graph'), className='twelve columns'),
    html.Div(dcc.Graph(id='mean14-graph'), className='twelve columns'),
    html.Div(dcc.Graph(id='exitus-graph'), className='twelve columns'),
    # tab_content_table,
    html.Div([html.I(className='fab fa-creative-commons'),
              html.I(className='fab fa-creative-commons-by'),
              html.I(className='far fa-copyright fa-flip-horizontal'),
              f" {footer_year} ", html.A("anuf",
                                         href="https://github.com/anuf",
                                         target="_blank"),
              " Todos os dereitos garantidos."],
             style={'textAlign': 'center',
                    'background': 'black',
                    'color': 'white'},
             className='twelve columns'
             )
])


# app.layout = html.Div(children=[
#     html.Img(src=app.get_asset_url('iconfinder-coronavirus-microscope-virus-laboratory-64.png'),
#              className='one columns'),
#     html.H1('Datos Coronavirus Sergas',
#             className='eleven columns',
#             ),
#     html.Div([
#         html.P("Indicador:", className='two columns'),
#         dcc.Dropdown(id='dropdown-parameter',
#                      options=[
#                          {'label': 'Pacientes con infección activa',
#                           'value': 'Pacientes con infección activa'},
#                          {'label': 'Casos confirmados por PCR nas últimas 24 horas',
#                           'value': 'Casos confirmados por PCR nas últimas 24 horas'},
#                          {'label': 'Hospitalizados hoxe',
#                           'value': 'Hospitalizados hoxe'},
#                          {'label': 'Falecidos',
#                           'value': 'Falecidos'},
#                          {'label': 'Contaxiados',
#                           'value': 'Contaxiados'},
#                          {'label': 'Curados',
#                           'value': 'Curados'},
#                          {'label': 'Probas PCR realizadas',
#                           'value': 'Probas PCR realizadas'},
#                          {'label': 'Probas serolóxicas realizadas',
#                           'value': 'Probas serolóxicas realizadas'},
#                          {'label': 'Coidados intensivos hoxe',
#                           'value': 'Coidados intensivos hoxe'},
#                          {'label': 'Diferenza de casos confirmados por PCR nas últimas 24 horas',
#                           'value': 'Diff Casos confirmados por PCR nas últimas 24 horas'},
#                          {'label': 'Diferenza de probas PCR realizadas con respecto ao día anterior',
#                           'value': 'Diff Probas PCR realizadas'},
#                          {'label': 'Diferenza de curados con respecto ao día anterior',
#                           'value': 'Diff Curados'},
#                          {'label': 'Diferenza de falecidos con respecto ao día anterior',
#                           'value': 'Diff Falecidos'}
#                      ],
#                      value='Casos confirmados por PCR nas últimas 24 horas',
#                      clearable=False,
#                      className='ten columns'
#                      )],
#     ),
#     html.Div([
#         html.P("Datas:", className='two columns'),
#         dcc.DatePickerRange(
#             id='date-picker',
#             start_date=s_date,
#             end_date=e_date,
#             display_format='D-M-Y',
#             className='ten columns',
#             first_day_of_week=1,
#             min_date_allowed='2020-10-07'
#         )
#     ]),
#     html.Div([
#         html.P("Área Sanitaria:", className='two columns'),
#         dcc.Dropdown(id='dropdown-area',
#                      options=[{'label': 'Galicia',
#                                'value': 'GALICIA'},
#                               {'label': 'A Coruña',
#                                'value': 'A.S. A CORUÑA E CEE'},
#                               {'label': 'Lugo',
#                                'value': 'A.S. LUGO, A MARIÑA E MONFORTE'},
#                               {'label': 'Ourense',
#                                'value': 'A.S. OURENSE, VERÍN E O BARCO'},
#                               {'label': 'Pontevedra',
#                                'value': 'A.S. PONTEVEDRA E O SALNÉS'},
#                               {'label': 'Vigo',
#                                'value': 'A.S. VIGO'},
#                               {'label': 'Santiago',
#                                'value': 'A.S. SANTIAGO E BARBANZA'},
#                               {'label': 'Ferrol',
#                                'value': 'A.S. FERROL'}
#                               ],
#                      value=['GALICIA',
#                             'A.S. A CORUÑA E CEE',
#                             'A.S. LUGO, A MARIÑA E MONFORTE',
#                             'A.S. OURENSE, VERÍN E O BARCO',
#                             'A.S. PONTEVEDRA E O SALNÉS',
#                             'A.S. VIGO',
#                             'A.S. SANTIAGO E BARBANZA',
#                             'A.S. FERROL'],
#                      multi=True,
#                      clearable=False,
#                      className='ten columns')
#     ]),
#     html.Div([
#         html.P("Disposición:", className='two columns'),
#         dcc.RadioItems(
#             id='radio-buttons',
#             options=[
#                 {'label': 'Agrupado', 'value': 'group'},
#                 {'label': 'Apilado', 'value': 'stack'}
#             ],
#             value='group',
#             labelStyle={'display': 'inline-block'},
#             className='ten columns'),
#     ]),
#     html.Hr(className='twelve columns'),
#     html.Div(dcc.Graph(id='main-graph'), className='twelve columns'),
#     html.Div(dcc.Graph(id='mean7-graph'), className='twelve columns'),
#     html.Div(dcc.Graph(id='mean14-graph'), className='twelve columns'),
#     html.Div([html.I(className='fab fa-creative-commons'),
#               html.I(className='fab fa-creative-commons-by'),
#               html.I(className='far fa-copyright fa-rotate-180'),
#               f" {ano} ", html.A("anuf",
#                                  href="https://github.com/anuf",
#                                  target="_blank"),
#               " Todos os dereitos garantidos."],
#              style={'textAlign': 'center',
#                     'background': 'black',
#                     'color': 'white'},
#              className='twelve columns'
#     )
# ])


@app.callback(
    [Output('main-graph', 'figure'),
     Output('mean7-graph', 'figure'),
     Output('mean14-graph', 'figure'),
     Output('exitus-graph', 'figure')],
    [Input('dropdown-parameter', 'value'),
     Input('date-picker', 'start_date'), Input('date-picker', 'end_date'),
     Input('radio-buttons', 'value'),
     Input('dropdown-area', 'value')
     ])
def update_figure(dd_parameter, start_date, end_date, rb_value, dd_area):
    df_to_figure = pd.DataFrame()
    if len(dd_area) > 0:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()  # datetime.date().fromisoformat(start_date)

        df_to_figure = main_df_extended[main_df_extended.Data.between(start_date, end_date)]

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
    elif dd_parameter == 'Novos positivos':
        fig_mean7_to_update = px.bar(df_to_figure,
                                     x='Data',
                                     y='Media 7 días Novos positivos',
                                     text='Media 7 días Novos positivos',
                                     title='Media Novos Positivos (7 días)',
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
                                      y='Media 14 días Novos positivos',
                                      text='Media 14 días Novos positivos',
                                      title='Media Novos Positivos (14 días)',
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
    elif dd_parameter == 'Pacientes con infección activa':
        fig_mean7_to_update = px.bar(df_to_figure,
                                     x='Data',
                                     y='Incidencia 7 días Casos Activos',
                                     text='Incidencia 7 días Casos Activos',
                                     title='Inciencia Media Casos Activos (7 días) por 100000 habs',
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
                                      y='Incidencia 14 días Casos Activos',
                                      text='Incidencia 14 días Casos Activos',
                                      title='Inciencia Media Casos Activos (14 días) por 100000 habs',
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

    activos_curados_falecidos_extended = pd.concat([
        activos_curados_falecidos_df, activos_curados_falecidos_df[
            ['Exitus']
        ].diff(periods=8).rename({
            'Exitus': 'Falecidos Diarios'
        },
            axis=1)],
        axis=1)

    activos_curados_falecidos_extended['Media 7 días'] = \
        activos_curados_falecidos_extended.groupby('Área Sanitaria')['Falecidos Diarios'].rolling(
            window=7).mean().reset_index(0, drop=True)

    activos_curados_falecidos_to_figure = activos_curados_falecidos_extended[
        activos_curados_falecidos_extended['Área Sanitaria'].isin(dd_area)]
    if dd_parameter == 'Falecidos':
        fig_exitus_to_update = plot_exitus(activos_curados_falecidos_to_figure)
    else:
        fig_exitus_to_update = {}

    return fig_to_update, fig_mean7_to_update, fig_mean14_to_update, fig_exitus_to_update


def plot_exitus(df_to_figure):
    fig_to_update = px.area(df_to_figure,
                            x='Data',
                            y='Falecidos Diarios',
                            # text='Falecidos Diarios',
                            title='Falecidos Diarios',
                            line_group='Área Sanitaria',
                            color="Área Sanitaria")

    fig_to_update.update_layout(title_x=0.5, yaxis={'title': ''})
    return fig_to_update


if __name__ == '__main__':
    app.run_server(debug=True)
