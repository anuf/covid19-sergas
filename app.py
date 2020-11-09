# -*- coding: utf-8 -*-
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

import os

import geopandas as gpd
import pandas as pd
import requests
from io import StringIO

import plotly.express as px

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import datetime

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

# Create a GeoJSON for maps outside US

# download Galicia data from http://mapas.xunta.gal/centro-de-descargas
lga_gdf = gpd.read_file('./data/Concellos_IGN/Concellos_IGN.shp')  # load the data using Geopandas

''' Data structure
INSPIREID       object  ES.IGN.SIGLIM34123636010
COUNTRY         object  ES
NATLEV          object  https://inspire.ec.europa.eu/codelist/Administ
NATLEVNAME      object  Municipio
NATCODE         object  34123636010
NAMEUNIT        object  Catoira
CODNUT1         object  ES1
CODNUT2         object  ES11
CODNUT3         object  ES114
NomeConcel      object  Catoira
CodCONC        float64  36010.0
Concello        object  Catoira
CodCOM         float64  45.0
CodPROV        float64  36.0
NomeCapita      object  Catoira
Comarca         object  Caldas
Provincia       object  Pontevedra
CODIGOINE       object  36010
NomeMAY         object  CATOIRA
Shape_Leng     float64  24670.212288
Shape_Area     float64  2.927458e+07
geometry      geometry  MULTIPOLYGON (((521479.446 4723459.689, 521470...
'''

# data to join
orig_url = 'https://docs.google.com/spreadsheets/d/16uJAVv8PDcDpENwMo68m7hiJAcl39pfPDyjUesodHIo/edit?usp=sharing'
dwn_url = orig_url.replace('edit?usp=sharing', 'export?format=csv')

url = requests.get(dwn_url).text.encode('latin-1').decode('utf-8')
csv_raw = StringIO(url)
df = pd.read_csv(csv_raw, header=0, dtype={"CP": str})

df = df.dropna()
df[['Total habitantes', 'Homes', 'Mulleres']] = df[['Total habitantes', 'Homes', 'Mulleres']].apply(pd.to_numeric)

# merge data and geo-spatial data

df_merged = pd.merge(lga_gdf[['CODIGOINE', 'geometry']], df[['CP', 'Concello', 'Total habitantes']],
                     left_on='CODIGOINE', right_on='CP', how='left')
df_merged = df_merged.dropna(subset=['Total habitantes', 'geometry']).set_index('CODIGOINE')

df_merged.head(3)

# fig, ax = plt.subplots(1,1, figsize=(20,20))
# divider = make_axes_locatable(ax)
# tmp = df_merged.copy()
# #tmp['Total habitantes'] = tmp['Total habitantes']*100 #To display percentages
# cax = divider.append_axes("right", size="3%", pad=-1) #resize the colorbar
# tmp.plot(column='Total habitantes', ax=ax,cax=cax,  legend=True,
#          legend_kwds={'label': "Total habitantes"})
# tmp.geometry.boundary.plot(color='#BABABA', ax=ax, linewidth=0.3) #Add some borders to the geometries
# ax.axis('off')
# fig.show()


# convert data to geojson
df_merged = df_merged.to_crs(epsg=4326)  # convert the coordinate reference system to lat/long
lga_json = df_merged.__geo_interface__  # convert to geoJSON

# Choropleth map using plotly.express and carto base map (no token needed)
# With px.choropleth_mapbox, each row of the DataFrame is represented as a region of the choropleth.
fig = px.choropleth_mapbox(df,
                           geojson=df_merged.geometry,
                           locations='CP',  # df_merged.index,
                           color='Total habitantes',  # df_merged['Total habitantes'],
                           hover_name="Concello",
                           # range_color
                           # center={"lat": 40.71, "lon": -74.00},
                           mapbox_style="carto-positron",  # mapbox_style="open-street-map"
                           zoom=6,
                           center={"lat": 42.88052, "lon": -8.54569}  # centered in Santiago de Compostela
                           )

fig2 = px.choropleth_mapbox(df,
                            geojson=df_merged.geometry,
                            locations='CP',  # df_merged.index,
                            color='Área Sanitaria',  # df_merged['Total habitantes'],
                            hover_name="Concello",
                            # range_color
                            # center={"lat": 40.71, "lon": -74.00},
                            mapbox_style="carto-positron",  # mapbox_style="open-street-map"
                            zoom=6,
                            center={"lat": 42.88052, "lon": -8.54569}  # centered in Santiago de Compostela
                            )

SPREADSHEET_ID = '1RAQvyqBq3o9d0ELBxBgBfX20xmG3jBk4wtwxt3Xdkh8'
RANGE_NAME = 'Datos xerais'


def get_google_sheet(spreadsheet_id, range_name):
    """ Retrieve sheet data using OAuth credentials and Google Python API. """
    scopes = 'https://www.googleapis.com/auth/spreadsheets.readonly'
    # Setup the Sheets API
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('./client_secret.json', scopes)
        creds = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=creds.authorize(Http()))

    # Call the Sheets API
    g_sheet = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    return g_sheet


def gsheet2df(gsheet):
    """ Converts Google sheet data to a Pandas DataFrame.
    Note: This script assumes that your data contains a header file on the first row!

    Also note that the Google API returns 'none' from empty cells - in order for the code
    below to work, you'll need to make sure your sheet doesn't contain empty cells,
    or update the code to account for such instances.

    """
    header = gsheet.get('values', [])[0]   # Assumes first line is header!
    values = gsheet.get('values', [])[1:]  # Everything else is data.
    if not values:
        print('No data found.')
    else:
        all_data = []
        for col_id, col_name in enumerate(header):
            column_data = []
            for row in values:
                column_data.append(row[col_id])
            ds = pd.Series(data=column_data, name=col_name)
            all_data.append(ds)
        df = pd.concat(all_data, axis=1)
        return df


gsheet = get_google_sheet(SPREADSHEET_ID, RANGE_NAME)
df_diarios = gsheet2df(gsheet)

df_diarios[['Pacientes con infección activa',
            'Hospitalizados hoxe', 'Coidados intensivos hoxe', 'Curados',
            'Falecidos', 'Contaxiados',
            'Casos confirmados por PCR nas últimas 24 horas',
            'Probas PCR realizadas', 'Probas serolóxicas realizadas']] = \
    df_diarios[['Pacientes con infección activa',
                'Hospitalizados hoxe', 'Coidados intensivos hoxe', 'Curados',
                'Falecidos', 'Contaxiados',
                'Casos confirmados por PCR nas últimas 24 horas',
                'Probas PCR realizadas', 'Probas serolóxicas realizadas']].apply(pd.to_numeric)
df_diarios[['Data']] = df_diarios[['Data']].apply(pd.to_datetime)

df_diarios_extended = pd.concat([
    df_diarios, df_diarios[
        ['Pacientes con infección activa',
         'Hospitalizados hoxe', 'Coidados intensivos hoxe', 'Curados',
         'Falecidos', 'Contaxiados', 'Casos confirmados por PCR nas últimas 24 horas',
         'Probas PCR realizadas', 'Probas serolóxicas realizadas']
    ].diff(periods=-8).rename({
        'Pacientes con infección activa': 'Diff Pacientes con infección activa',
        'Hospitalizados hoxe': 'Diff Hospitalizados hoxe',
        'Coidados intensivos hoxe': 'Diff Coidados intensivos hoxe',
        'Curados': 'Diff Curados',
        'Falecidos': 'Diff Falecidos',
        'Contaxiados': 'Diff Contaxiados',
        'Casos confirmados por PCR nas últimas 24 horas': 'Diff Casos confirmados por PCR nas últimas 24 horas',
        'Probas PCR realizadas': 'Diff Probas PCR realizadas',
        'Probas serolóxicas realizadas': 'Diff Probas serolóxicas realizadas'
    },
        axis=1)],
    axis=1)


df_diarios_extended['Date'] = [datetime.datetime.date(d) for d in df_diarios_extended['Data']]
df_24h = df_diarios_extended.head(8)

df_merged2 = pd.merge(df_diarios_extended[['Área Sanitaria', 'Casos confirmados por PCR nas últimas 24 horas']],
                      df[['CP', 'Concello', 'Total habitantes', 'Homes', 'Mulleres', 'Área Sanitaria']],
                      left_on='Área Sanitaria', right_on='Área Sanitaria', how='left')

df_merged2['areacolor'] = df_merged2['Área Sanitaria']
print(set(df_merged2['Área Sanitaria']))
print(set(df['Área Sanitaria']))
dic_areas = {'Galicia': 0,
             'A Coruña': 1,
             'Lugo': 2,
             'Ourense': 3,
             'Pontevedra': 4,
             'Vigo': 5,
             'Santiago': 6,
             'Ferrol': 7}
df_merged2['areacolor'] = df_merged2['areacolor'].map(dic_areas)

fig4 = px.choropleth_mapbox(df,
                            geojson=df_merged.geometry,
                            locations='CP',  # df_merged.index,
                            color='Área Sanitaria',  # df_merged['Total habitantes'],
                            hover_name="Concello",
                            # range_color
                            # center={"lat": 40.71, "lon": -74.00},
                            mapbox_style="carto-positron",  # mapbox_style="open-street-map"
                            zoom=6,
                            center={"lat": 42.88052, "lon": -8.54569}  # centered in Santiago de Compostela
)

x = datetime.datetime.now().date() - datetime.timedelta(8)

df_filtered = df_diarios_extended[df_diarios_extended["Date"] >= datetime.datetime.now().date() - datetime.timedelta(7)]
print("MinMAX {} {}".format(min(df_diarios_extended["Date"]), max(df_diarios_extended["Date"])))

e_date = max(df_filtered['Date'])
s_date = e_date - datetime.timedelta(1)

app.layout = html.Div(children=[
    html.H1('Datos Coronavirus Sergas'),
    html.Div([
        html.P("Indicador:", className='two columns'),
        dcc.Dropdown(id='dropdown-parameter',
                     options=[{'label': 'Casos confirmados por PCR nas últimas 24 horas',
                               'value': 'Casos confirmados por PCR nas últimas 24 horas'},
                              {'label': 'Hospitalizados hoxe',
                               'value': 'Hospitalizados hoxe'},
                              {'label': 'Falecidos',
                               'value': 'Falecidos'},
                              {'label': 'Contaxiados',
                               'value': 'Contaxiados'},
                              {'label': 'Coidados intensivos hoxe',
                               'value': 'Coidados intensivos hoxe'}
                              ],
                     value='Hospitalizados hoxe',
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
            className='ten columns'
        )
    ]),
    html.Div([
        html.P("Área Sanitaria:", className='two columns'),
        dcc.Dropdown(id='dropdown-area',
                     options=[{'label': 'Galicia',
                               'value': 'Galicia'},
                              {'label': 'A Coruña',
                               'value': 'A Coruña'},
                              {'label': 'Lugo',
                               'value': 'Lugo'},
                              {'label': 'Ourense',
                               'value': 'Ourense'},
                              {'label': 'Pontevedra',
                               'value': 'Pontevedra'},
                              {'label': 'Vigo',
                               'value': 'Vigo'},
                              {'label': 'Santiago',
                               'value': 'Santiago'},
                              {'label': 'Ferrol',
                               'value': 'Ferrol'}
                              ],
                     value=['Galicia',
                            'A Coruña',
                            'Lugo',
                            'Ourense',
                            'Pontevedra',
                            'Vigo',
                            'Santiago',
                            'Ferrol'],
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
            value='stack',
            labelStyle={'display': 'inline-block'},
            className='ten columns'),
    ]),

    html.Div(dcc.Graph(id='example-graph'), className='twelve columns'),
    html.Div(dcc.Graph(id='example-graph0', figure=fig4), className='six columns')
])


@app.callback(
    Output('example-graph', 'figure'),
    [Input('dropdown-parameter', 'value'),
     Input('date-picker', 'start_date'), Input('date-picker', 'end_date'),
     Input('radio-buttons', 'value'),
     Input('dropdown-area', 'value')
     ])
def update_figure(dd_parameter, start_date, end_date, rb_value, dd_area):

    s_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()  # datetime.date().fromisoformat(start_date)
    e_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()  # datetime.date().fromisoformat(start_date)

    df_to_figure = df_diarios_extended[df_diarios_extended.Date.between(s_date, e_date)]

    df_to_figure = df_to_figure[df_to_figure['Área Sanitaria'].isin(dd_area)]

    fig_to_update = px.bar(df_to_figure,
                           x='Date',
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

    return fig_to_update


if __name__ == '__main__':
    app.run_server(debug=True)

