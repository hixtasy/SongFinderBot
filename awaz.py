import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from base64 import b64encode
from time import time
from pydub import AudioSegment
from algorithm import SignatureGenerator
import os, re
from urllib.parse import quote

def find_insta(short):
    headers = <INSTAGRAM_DUMMY_ACCOUNT_TOKENS_HEADER>
    params = (
        ('clips_media_shortcode', short),
    )
    res = requests.get('https://i.instagram.com/api/v1/clips/item/', headers=headers, params=params)
    if res.status_code == 200:
        try:
            try:
                uri = res.json()['media']['clips_metadata']['original_sound_info']['progressive_download_url']
            except:
                uri = res.json()['media']['clips_metadata']['music_info']['music_asset_info']['progressive_download_url']
            return uri
        except:
            return False
    else:
        return False
        
def bs_voice(input):
    audio = AudioSegment.from_file(input)

    audio = audio.set_sample_width(2)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)

    signature_generator = SignatureGenerator()
    signature_generator.feed_input(audio.get_array_of_samples())

    signature_generator.MAX_TIME_SECONDS = 12
    if audio.duration_seconds > 12 * 3:
        signature_generator.samples_processed += 16000 * (int(audio.duration_seconds / 2) - 6)

    return signature_generator.get_next_signature().encode_to_uri()

def json_to_msg(jsn):
    if len(jsn['matches']) > 0:
        jsd = {}
        jsd['status'] = True
        jsd['message'] = 'Wohooo! I detected this song!\n'
        jsd['Name'] = jsn['track']['title']
        jsd['Artist'] = jsn['track']['subtitle']
        try:
            jsd['image'] = jsn['track']['images']['coverarthq']
        except:
            pass
        return jsd
    else:
        return {"status": False, "message": "Sorry! No results found, Try again!"}

def save_file(url):
    data = requests.get(url).content
    file_name = url.split('/')[-1].split('?')[0]
    di = 'Temp/'
    with open(di+file_name, 'wb') as wr:
        wr.write(data)
    return di+file_name

def del_file(name):
    os.remove(name)

def voiceToSong(uri):
    ts = str(int(time())*1000)
    headers = {
        'Host': 'amp.shazam.com',
        'content-type': 'application/json',
        'accept-encoding': 'gzip',
        'user-agent': 'Dalvik/2.1.0 (Linux; U; Android 9; POCO F1 Build/PQ3A.190801.002) Shazam/v10.41.0',
        'content-language': 'en_US',
    }

    params = (
        ('sync', 'true'),
        ('webv3', 'true'),
        ('sampling', 'true'),
        ('connected', ''),
        ('shazamapiversion', 'v3'),
        ('sharehub', 'true'),
        ('video', 'v3'),
    )
    data = '{"signature":{"samplems":5760,"timestamp":'+ts+',"uri":"'+uri+'"},"timezone":"Asia/Kolkata","timestamp":'+ts+'}'
    #print(uri)
    res = requests.post('https://amp.shazam.com/discovery/v5/en-US/US/android/-/tag/0AA04766-F35B-45A1-A3C6-337193807BCD/a7721217-808e-472d-a796-48c5e351be59', headers=headers, params=params, data=data)
    return res.json()


def welcome(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(f'Hi {update.effective_user.first_name}, I hope you are doing well!\nJust play any unknown song, record it via voice note or paste instagram reels link and send me, I will recognize and send you the song name!')

def image_handler(update: Update, context: CallbackContext) -> None:
    file = False
    try:
        file = context.bot.getFile(update.message.voice.file_id)['file_path']
    except:
        pass
    try:
        ff = re.findall('^(?:.*\/reel\/)([\d\w\-_]+)', update.message.text)
        if len(ff) > 0:
            file = find_insta(ff[0])
        else:
            update.message.reply_text("Sorry! Currently we do not support this platform")
            return False
    except:
        pass
    if file == False:
        update.message.reply_text("Oops! There was an error, please contact bot owner for fix")
        return False
    f_name = save_file(file)
    bs64 = bs_voice(f_name)
    jsn_data = voiceToSong(bs64)
    msg = json_to_msg(jsn_data)
    #print(msg)
    if msg['status'] == True:
        caption = ""
        for key, value in msg.items():
            if(key != 'image') and (key != 'status'):
                if key == 'message':
                    caption += str(value)+"\n"
                else:
                    caption += str(key)+": "+str(value)+"\n"
        sp_url = f"https://open.spotify.com/search/{quote(msg['Name'])}"
        yt_url = f"https://m.youtube.com/results?search_query={quote(msg['Name'])} {quote(msg['Artist'])}"

        markup = InlineKeyboardMarkup([[InlineKeyboardButton(text='Open in YouTube App', url=yt_url)],[InlineKeyboardButton(text='Open in Spotify App', url=sp_url)]])
        if 'image' not in str(msg):
            #print('Caption Only')
            update.message.reply_text(caption, reply_markup=markup)
        else:
            #print('Image and Caption')
            update.message.reply_photo(photo=msg['image'], caption=caption, reply_markup=markup)
    elif msg['status'] == False:
        update.message.reply_text(msg['message'])
    #print(msg)
    del_file(f_name)

updater = Updater(<TELEGRAM_BOT_TOKEN_HERE>)
updater.dispatcher.add_handler(CommandHandler('start', welcome))
updater.dispatcher.add_handler(MessageHandler((Filters.voice | Filters.text), image_handler))

updater.start_polling()
updater.idle()