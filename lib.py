import pandas as pd
import time
import sqlite3
import datetime
from selenium import webdriver
from pathlib import Path
import traceback

def load_chromedriver(en_casa):
    """
    Loads chromedriver from path
    
    Args:
        en_casa (bool): directory at home with linux or not
    """
    if en_casa:
        driver = webdriver.Chrome(r'../../../../chromedriver')
    else:
        driver = webdriver.Chrome(r"C:\Users\manuel.lopez\Documents\chromedriver.exe")
        
    try:
        driver.maximize_window()
    except:
        pass
    
    
    return driver

        
competition_families = {
    'World Championships': ['World Championships'],
    'Masters': ['Masters'],
    'Grand Prix': ['Grand Prix'],
    'Grand Slam': ['Grand Slam'],
    'Olympic Games': ['Olympic Games'],
    'Continental Championships': [
        'European Championships',
        'Panamerican Championships',
        'Asian Championships',
        'African Championships',
        'Oceanian Championships'
    ],
    'Continental Open': [
        'World Cup',
        'Continental Cup',
        'European Open',
        'Panamerican Open',
        'Asian Open',
        'African Open',
        'Oceanian Open',
    ]
}

competition_to_family_map = {element: family for family in competition_families.keys() for element in competition_families[family]}


url_leaders_by_weight = {
    'men_60': 'https://judobase.ijf.org/#/wrl/1/simple',
    'men_66': 'https://judobase.ijf.org/#/wrl/2/simple',
    'men_73': 'https://judobase.ijf.org/#/wrl/3/simple',
    'men_81': 'https://judobase.ijf.org/#/wrl/4/simple',
    'men_90': 'https://judobase.ijf.org/#/wrl/5/simple',
    'men_100': 'https://judobase.ijf.org/#/wrl/6/simple',
    'men_100+': 'https://judobase.ijf.org/#/wrl/7/simple',
    'women_48': 'https://judobase.ijf.org/#/wrl/8/simple',
    'women_52': 'https://judobase.ijf.org/#/wrl/9/simple',
    'women_57': 'https://judobase.ijf.org/#/wrl/10/simple',
    'women_63': 'https://judobase.ijf.org/#/wrl/11/simple',
    'women_70': 'https://judobase.ijf.org/#/wrl/12/simple',
    'women_78': 'https://judobase.ijf.org/#/wrl/13/simple',
    'women_78+': 'https://judobase.ijf.org/#/wrl/14/simple'
}


def category_map(category):
    '''
    Turns '-52 kg' into 'women_52'
    '''
    men = ['60', '66', '73', '81', '90', '100']
    women = ['48', '52', '57', '63', '70', '78']
    temp = category.split()[0]
    menos = temp[0] == '-'
    peso = temp[1:]
    
    new_category = ('men_' if peso in men else 'women_') + peso + ('+' if not menos else '')
    
    return new_category


def get_all_battles(driver, profile_id, from_date, time_sleep=0.1):
    """
    Extracts all contests information of a profile, including video url.
    
    Args:
        driver (selenium.webdriver): driver to interact with the web via selenium
        profile_id (str): string integer, id of competitor
        from_date (datetime.datetime): extract contests only after this date
        time_sleep (float): time to wait after clicking play to video url
    """
    # how to treat the text of each column in the web
    columns_map = {
        1: 'wins',
        3: 'opponent',
        5: 'local_points',
        7: 'opponent_points',
        8: 'duration',
        9: 'date',
        10: 'event',
        11: 'category',
        12: 'round',
    }
    
    treatment_battle = {
        'wins': lambda win_local: 1 if win_local == 'won' else 0,
        'opponent': lambda name: name.replace('\n', ' '),
        'local_points': lambda points: points.replace(' ', ''),
        'opponent_points': lambda points: points.replace(' ', ''),
        'duration': lambda x: x,
        'date': lambda date: datetime.datetime.strptime(date, '%d %b %Y'),
        'event': lambda comp: comp.replace('\n', ' '),
        'category': lambda x: x,
        'round': lambda x: x
    }
    
    # start crawling
    profile_web = 'https://judobase.ijf.org/#/competitor/profile/' + profile_id
    numero_petes = 0
    driver.get(profile_web)
    time.sleep(1)
    try:
        driver.maximize_window()
    except:
        pass
    time.sleep(1)
    
    # extract name
    profile_name = driver.find_element_by_class_name('title').text.replace('\n', ' ')
    print(f'Extracting info from: {profile_name}...')
    
    # extract Contests info
    driver.find_element_by_xpath('//a[@data-view="contests"]').click()
    time.sleep(1)
    tabla = driver.find_element_by_tag_name('tbody')
    assert tabla.get_attribute('role') == 'alert', 'No encontró la tabla apropiada en Contests'
    
    battles = list()
    filas = tabla.find_elements_by_tag_name('tr')
    
    for rowindex, row in enumerate(filas):
        battle = {}
        for colindex, value in enumerate(row.find_elements_by_tag_name('td')):
            if colindex in columns_map.keys():
                # print(colindex, value.text)
                colname = columns_map[colindex]
                battle[colname] = treatment_battle[colname](value.text)
            elif colindex == 13:
                # tiene o no video
                battle['has_video'] = len(value.find_elements_by_tag_name('div')) > 0
        
        if battle['date'] <= from_date:
            break
        # else
        battles.append(battle)
    
    if len(battles) == 0:
        print('Up to date!')
        return None
    
    battles = pd.DataFrame(battles)
    
    number_of_videos = battles.has_video.sum()
    
    # extraer video urls
    print('Extracting video URLs...')
    contests_url = driver.current_url
    play_buttons = driver.find_elements_by_xpath("//div[contains(@class, 'btn') and contains(@class, 'btn-sm') "
                                                 "and contains(@class, 'btn-default')]")
    urls = list()
    
    for play_index in range(number_of_videos):
        while True:
            try:
                # hay que hacerlo asi porque el loop pierde el norte al clickear
                driver.get(contests_url)
                time.sleep(time_sleep)
                play = driver.find_elements_by_xpath("//div[contains(@class, 'btn') and contains(@class, 'btn-sm') "
                                                     "and contains(@class, 'btn-default')]")[play_index]
                play.click()
                time.sleep(time_sleep)
                urls.append(driver.current_url)
                # solo llega aquí si no peta. si peta, repite
                break
            except:
                numero_petes += 1
                pass
            
    battles.loc[battles.has_video, 'url_video'] = urls
    
    
    battles['local'] = profile_name
    battles['competition_family'] = battles.event.apply(
        lambda event: next((competition_to_family_map[c] for c in competition_to_family_map.keys() if c in event), 'Other'))
    
    battles.category = battles.category.apply(category_map)
    
    column_order = ['wins', 'local', 'opponent', 'event', 'date', 'round', 
                    'local_points', 'opponent_points', 'duration', 'category', 
                    'has_video', 'competition_family', 'url_video']
    battles = battles[column_order]
    
    
    return battles


def update_competitor(driver, conn, profile_id):
    """
    Given profile_id of competitor:
      1. Extracts new battles since competitor's last extraction
      2. Appends new battles to battles table
      3. Updates last_extraction value for this competitor
      
    Args:
        driver (selenium.webdriver): to connect to web browser via selenium
        conn (SQLiteConnection): connection to sql file containing tables competitors, battles
        profile_id (str): profile_id of competitor: 3238, 17332, 569...
    """
    # when did last_extraction happen for this competitor?
    last_extraction = conn.as_pandas(
        f'select last_extraction from competitors where profile_id="{profile_id}"', 
        parse_dates=['last_extraction']
    ).iloc[0,0]
    
    # extract new battles
    new_battles = get_all_battles(
        driver=driver,
        profile_id=profile_id, 
        from_date=last_extraction
    )
    
    if new_battles is not None:
        print('new battles!')
        # append new_battles to battles table
        conn.append_table('battles', new_battles)
        # update last_extraction in competitors table
        last_extraction_str = str(new_battles.date.max())
        conn.query(
            f'''
            UPDATE competitors 
            SET last_extraction="{last_extraction_str}" 
            WHERE profile_id="{profile_id}";
            '''
        )
        

def extract_all_profiles_weight(driver, weight):
    """
    Extract top100 competitors of given weight: name, country, profile_url. Not the WRL points, that changes much and we don't need it
    
    Args:
        driver (selenium.webdriver): driver to interact with the web via selenium
        weight (str): one of men_60, men_100+, women_70...
        
    Return:
        competitors (pd.DataFrame): summary of top100 competitors
    """
    # access url
    url_top = url_leaders_by_weight[weight]

    driver.get(url_top)
    time.sleep(1)
    try:
        driver.maximize_window()
    except:
        pass
    time.sleep(1)

    
    # extract info
    tabla = driver.find_element_by_tag_name('tbody')
    assert tabla.get_attribute('role') == 'alert', 'Expected table not found'

    # how to treat the text of each column
    treatment_competitor = {
        2: lambda name: name.strip(),
        3: lambda country: country,
    }

    competitors = []
    for row in tabla.find_elements_by_tag_name('tr'):
        competitor = []
        for index, value in enumerate(row.find_elements_by_tag_name('td')):
            if index in treatment_competitor.keys():
                competitor.append(treatment_competitor[index](value.text))
            elif index == 1:
                profile_web = value.find_element_by_tag_name('img').get_attribute('src')
                cut_from, cut_to = profile_web[::-1].find('/'), profile_web[::-1].find('.')
                profile_id = profile_web[-cut_from : -cut_to - 1]

        competitor.append(profile_id)
        competitors.append(competitor)


    competitors = pd.DataFrame(competitors, columns=['name', 'country', 'profile_id'])
    competitors['category'] = weight
    
    
    return competitors




    
    
    return local, opponent, url_youtube



class SQLiteConnection:
    def __init__(self, path, logger=None):
        """
        Class that abstracts the

        Args:
            path: (Path) Path to the database file
        """
        if not isinstance(path, Path):
            path = Path(path)

        try:
            self.connection = sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True)
        except sqlite3.OperationalError:
            raise sqlite3.OperationalError(f'Unable to open {str(path.absolute())}')
        self.path = path
        self.logger = logger

        
    def query(self, query_string, values=None, empty_response=False, lastrowid=False):
        cursor = self.connection.cursor()
        if values is None:
            cursor.execute(query_string)
            self.connection.commit()
        else:
            cursor.execute(query_string, values)
            self.connection.commit()
        if empty_response and lastrowid:
            return cursor.lastrowid
        elif empty_response and not lastrowid:
            return
        elif lastrowid and not empty_response:
            return cursor.fetchall(), cursor.lastrowid
        else:
            return cursor.fetchall()

    def as_pandas(self, query_string, index_col=None, parse_dates=None, columns=None, params=None):
        """
        Return query as pandas data frame

        Args:
            query_string: SQL valid query
            index_col: Column to be used as index
            parse_dates: See pandas.read_sql parse_dates
            columns: See pandas.read_sql columns
            params: See pandas.read_sql params
        
        Returns: 
            A pandas.DataFrame
        """
        return pd.read_sql(query_string, self.connection, index_col=index_col, 
                           parse_dates=parse_dates, columns=columns, params=params)


    def commit(self):
        self.connection.commit()


    def add_table(self, name, df: pd.DataFrame, if_exists='replace', index=False):
        """
        Add a dataframe to the table

        Args:
            name: Name of the table
            df: Dataframe to be written to
            if_exists(str): {‘fail’, ‘replace’, ‘append’}, default ‘fail’.

        """
        try:
            assert isinstance(df, pd.DataFrame)
        except AssertionError as e:
            if self.logger is not None:
                self.logger.exception(e)
            raise TypeError('df, Expected type pandas.DataFrame or geopandas.GeoDataFrame')

        df.to_sql(name=name, con=self.connection, if_exists=if_exists, index=index)

        
    def append_table(self, name, df: pd.DataFrame):
        """
        Append a dataframe to the table

        Args:
            name: Name of the table
            df: Dataframe to be written to
        
        Returns:
        """
        try:
            assert isinstance(df, pd.DataFrame)
        except AssertionError as e:
            if self.logger is not None:
                self.logger.exception(e)
            raise TypeError('df, Expected type pandas.DataFrame or geopandas.GeoDataFrame')

        df.to_sql(name=name, con=self.connection, if_exists='append')

        
    def drop_table(self, table_name):
        try:
            self.query("drop table {}".format(table_name))

        except sqlite3.OperationalError:
            if self.logger is not None:
                self.logger.warning(f"Trying to drop a table that does not exist: {table_name}")

                
    def query_all(self, table_name):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM {}".format(table_name))
        return cursor.fetchall()

    
    def query_all_as_pandas(self, table_name, index_col=None, parse_dates=None, columns=None, params=None):
        """
        Return query as pandas data frame

        :param table_name: Name of table to extract
        :param index_col: Column to be used as index
        :param parse_dates: See pandas.read_sql parse_dates
        :param columns: See pandas.read_sql columns
        :param params: See pandas.read_sql params
        :return: A pandas.DataFrame
        """
        return pd.read_sql('SELECT * FROM {}'.format(table_name), self.connection, index_col=index_col,
                           parse_dates=parse_dates, columns=columns, params=params)
    
    
    def count_rows(self, table_name):
        count = self.query('SELECT COUNT(*) FROM {}'.format(table_name))
        return count[0][0]
    
    
    def check_table_empty(self, table_name):
        if self.count_rows(table_name) == 0:
            return True
        else:
            return False

        
    def close(self):
        self.connection.close()
        
        
def get_info_video_judobase(competitor_name, driver, url_video):
    """
    Extracts local, opponent, and YOUTUBE url of embedded video in judobase
    
    Args:
        who (str): name of competitor
        driver (selenium.webdriver): driver to interact with the web via selenium
        url_video (str): url to video in judobase. 
            example: 'https://judobase.ijf.org/#/competition/contest/gs_jpn2017_m_p100_0004'
    """
    driver.get(url_video)
    
    
    try:
        time.sleep(1)
        # extract names
        local, opponent = map(lambda x: x.text, driver.find_elements_by_class_name('col-xs-6'))
        local, opponent = map(lambda x: x[:x.find('\n')], [local, opponent])

        is_local = (local == competitor_name)
        
    except Exception as err:
        try:
            time.sleep(2)
            alert = driver.switch_to_alert()
            alert.accept()
            print('popup error at ', url_video, err)
        except:
            traceback.print_exc()
            print(url_video)
            print('error', err)
    
    time.sleep(1)
    # extract names
    local, opponent = map(lambda x: x.text, driver.find_elements_by_class_name('col-xs-6'))
    local, opponent = map(lambda x: x[:x.find('\n')], [local, opponent])

    is_local = (local == competitor_name)

    # extract battle info
    try:
        # tabla con puntuaciones etiquetadas en tiempo
        tablas = driver.find_elements_by_tag_name('tbody')    
        tabla_timed_points = tablas[1] 
        filas = tabla_timed_points.find_elements_by_tag_name('tr')

        if len(filas) == 0:
            return []

        ncols = len(filas[0].find_elements_by_tag_name('td'))
        actions = []

        if ncols == 3:
            for row_number, row in enumerate(filas):
                cols = row.find_elements_by_tag_name('td')
                if cols[0].text:
                    you = 0 + is_local
                    what, what2 = cols[0].text.split('\n')[:2] + ([' '] if len(cols[0].text.split('\n')) == 1 else [])
                else:
                    you = 1 - is_local
                    what, what2 = cols[2].text.split('\n')[:2] + ([' '] if len(cols[2].text.split('\n')) == 1 else [])

                time_action = cols[1].text
                minutes, seconds = time_action.split(':')
                # url = url_youtube + '&t=' + str(60*int(minutes) + int(seconds))
                # will be returned instead of url_video if better

                if 'HSK' in what2:
                    what, what2 = what2, what

                actions.append((opponent if is_local else local, you, what, what2, time_action, url_video))
            '''    
            else:
                for row_number, row in enumerate(filas):
                    for col_number, value in enumerate(row.find_elements_by_tag_name('td')):
                        print(row_number, col_number, value.text)
            '''
            
        return actions
    
    except Exception as err:
        traceback.print_exc()
        print('error', err)
        
        return []
    
'''
        # extract YOUTUBE url
        count = 0
        while True:
            try:
                youtube_frame = driver.find_element_by_class_name('js-media')
                driver.switch_to.frame(youtube_frame)
                time.sleep(1)
                url_youtube = driver.find_element_by_class_name('ytp-title-link').get_attribute('href')
                break
            except:
                count += 1
                if count == 5:
                    url_youtube = 'error'
                    print('STOP Retry')
                    break

                print('Retry...')
                driver.get(url_video)
                time.sleep(1)
'''