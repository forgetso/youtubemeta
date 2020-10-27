from bs4 import BeautifulSoup
import random
from youtubemeta.useragents import user_agent_list
import argparse
import re
import json
import calendar
import time
import httpx
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd
from pathlib import Path

URL = 'https://www.youtube.com/user/{}/videos?flow=grid&sort=dd&view=0&app=desktop'
# choose a random user agent
USER_AGENT = random.choice(user_agent_list)
MORE_URL = 'https://www.youtube.com/browse_ajax?ctoken={}&continuation={}&itct={}'
BASE_URL = 'https://www.youtube.com'
CONTENT_START_SPLIT = '["ytInitialData"] = '
CONTENT_END_SPLIT = 'window["ytInitialPlayerResponse"]'
VARS_START_SPLIT = 'window.ytplayer = {};ytcfg.set('
VARS_END_SPLIT = ');ytcfg.set("SBOX_LABELS"'


def scrape(channel, write=None, path=None):
    if not path:
        path = Path('youtube-{}.csv'.format(channel))
    else:
        path = Path(path)
    with httpx.Client(http2=True) as session:

        headers = {'User-Agent': USER_AGENT}
        r = session.get(url=URL.format(channel), headers=headers)
        soup = BeautifulSoup(r.content, 'html.parser')
        all_scripts = soup.find_all('script')
        content_dict = extract_json_from_script(all_scripts, CONTENT_START_SPLIT, CONTENT_END_SPLIT, -1)
        vars_dict = extract_json_from_script(all_scripts, VARS_START_SPLIT, VARS_END_SPLIT)
        grid_renderer = get_grid_renderer(content_dict)
        videos = get_video_data(grid_renderer)
        continuation_url = get_more_videos_url(grid_renderer)
        while continuation_url is not None:
            more_videos, continuation_url = get_more_videos(session, channel, continuation_url, vars_dict)
            if more_videos:
                videos.extend(more_videos)
            time.sleep(1)
        if write:
            pd.DataFrame(videos).to_csv(str(path.absolute()), index=False)
    return videos


def get_more_videos(session, channel, continuation_url, vars_dict):
    print('Loading more videos from {}...'.format(continuation_url))
    headers = get_headers(channel, vars_dict)
    r = session.get(continuation_url, headers=headers)

    if failed_response(r.content):
        print('Failed getting more videos data. Server returned {}'.format(r.content))
        import pprint
        pprint.pprint(r.request.headers)
        exit()

    more_videos_response_str = decompress_content(r)
    more_videos_response = json.loads(more_videos_response_str)
    grid_renderer = get_grid_renderer(json=more_videos_response)
    videos = get_video_data(grid_renderer)
    continuation_url = get_more_videos_url(grid_renderer=grid_renderer)
    print('{} more videos added'.format(len(videos)))
    return videos, continuation_url


def decompress_content(request):
    encoding = request.headers.get('content-encoding')
    if encoding == 'br':
        import brotli
        content = brotli.decompress(request.content)
    elif encoding == 'gzip':
        import gzip
        content = gzip.decompress(request.content).decode()
    else:
        content = request.text
    return content


def failed_response(content):
    if content == b'{"reload":"now"}':
        return True
    else:
        return False


def extract_json_from_script(all_scripts, start_split, end_split, trim_length=None):
    parts = []
    for script in all_scripts:
        try:
            scriptstr = str(script)
            parts = scriptstr.split(start_split)
        except ValueError as e:
            print('Error in extract_json_from_script: {}'.format(e))
            pass
        if len(parts) > 1:
            break
    jsonstr = parts[1].split(end_split)[0].strip()
    if trim_length is not None:
        jsonstr = jsonstr[:trim_length]
    jsondict = json.loads(jsonstr)
    return jsondict


def get_video_data(grid_renderer):
    data = []
    try:
        for item in grid_renderer['items']:
            vid = {}
            renderer = item['gridVideoRenderer']
            if 'title' in renderer:
                vid['title'] = renderer['title']['runs'][0]['text']
                vid['view_count'] = renderer['viewCountText']['simpleText'].replace(' views', '')
                vid['date_simple'] = renderer['publishedTimeText']['simpleText']
                vid['date'] = parse_human_timedelta(vid['date_simple'])
                vid['url'] = BASE_URL
                vid['url'] += renderer['navigationEndpoint']['commandMetadata']['webCommandMetadata'][
                    'url']
                data.append(vid)
    except KeyError as e:
        print('Key error in get_video_data: {}'.format(e))
    return data


def get_grid_renderer(json):
    try:
        # contents.twoColumnBrowseResultsRenderer.tabs[1].tabRenderer.content.sectionListRenderer.contents[0].itemSectionRenderer.contents[0].gridRenderer
        grid_renderer = \
            json['contents']['twoColumnBrowseResultsRenderer']['tabs'][1]['tabRenderer']['content'][
                'sectionListRenderer'][
                'contents'][0]['itemSectionRenderer']['contents'][0]['gridRenderer']
    except (KeyError, TypeError):
        # $[1].response.continuationContents.gridContinuation.items[0].gridVideoRenderer
        grid_renderer = json[1]['response']['continuationContents']['gridContinuation']
    return grid_renderer


def parse_human_timedelta(delta):
    result = None
    try:
        time_measures = ['second', 'minute', 'hour', 'day', 'week', 'month', 'year']
        match = re.search('({})'.format('|'.join(time_measures)), delta)[0]
        params = {}
        for measure in time_measures:
            if measure in match:
                params['{}s'.format(measure)] = int(delta.split(' ')[0])
                break
        timedelta = relativedelta(**params)
        result = datetime.date(datetime.now() - timedelta)
    except KeyError as e:
        print('KeyError in parse_human_timedelta: {}'.format(e))
    return result


def get_more_videos_url(grid_renderer):
    url = None
    continuations = grid_renderer.get('continuations')
    if continuations:
        continuation = continuations[0]['nextContinuationData']['continuation'].replace('%3D', '%253D')
        clickTrackingParams = continuations[0]['nextContinuationData']['clickTrackingParams']
        url = MORE_URL.format(continuation, continuation, clickTrackingParams)
    return url


def get_headers(channel, yt_vars):
    previous = '{}/user/{}/videos?flow=grid&sort=dd&view=0'.format(BASE_URL, channel)
    headers = {  # ':authority': 'www.youtube.com',
        # ':method': 'GET',
        # ':path': url.replace(BASE_URL, ''),
        # ':scheme': 'https',
        'accept': '*/*',
        'accept-encoding': 'identity',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': previous,
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': USER_AGENT,
        'x-spf-previous': previous,
        'x-spf-referer': previous,
        'x-youtube-ad-signals': 'dt={}&flash=0&frm&u_tz=60&u_his=8&u_java&u_h=1080&u_w=1920&u_ah=1080&u_aw=1920&u_cd=24&u_nplug=2&u_nmime=2&bc=31&bih=980&biw=609&brdim=1920%2C0%2C1920%2C0%2C1920%2C0%2C1920%2C1080%2C624%2C980&vis=1&wgl=true&ca_type=image'.format(
            calendar.timegm(time.gmtime())),
        'x-youtube-client-name': '1',
        'x-youtube-client-version': yt_vars['INNERTUBE_CONTEXT_CLIENT_VERSION'],
        'x-youtube-device': 'cbr=Chrome&cbrver=86.0.4240.99&ceng=WebKit&cengver=537.36&cos=X11',
        # 'x-youtube-identity-token': yt_vars['ID_TOKEN'],
        'x-youtube-page-cl': yt_vars['PAGE_CL'],
        'x-youtube-page-label': yt_vars['PAGE_BUILD_LABEL'],
        'x-youtube-time-zone': 'Europe/London',
        'x-youtube-utc-offset': '0',
        'x-youtube-variants-checksum': yt_vars['VARIANTS_CHECKSUM']
    }
    headers = {k: str(v) for k, v in headers.items()}
    return headers


def setup():
    parser = argparse.ArgumentParser(description='Get channel data from youtube')
    parser.add_argument('channel', default=None, help="youtube channel")
    parser.add_argument('--write', action='store_true',
                        help="write to file (default filename is youtube_[channel].csv)")
    parser.add_argument('--path', default=None, help="specify file path")
    args = parser.parse_args()
    scrape(channel=args.channel, write=args.write, path=args.path)


if __name__ == "__main__":
    setup()
