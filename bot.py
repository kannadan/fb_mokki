
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, InlineQueryHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime
from dotenv import load_dotenv

import os.path

from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import itertools
from random import shuffle

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

token = os.getenv('token')

creds = service_account.Credentials.from_service_account_file(
    'credentials.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

# Set up the Sheets API client
service = build('sheets', 'v4', credentials=creds)

# Define the spreadsheet ID and range of cells to read
spreadsheet_id = os.getenv('sheet_id')
range_name = "'Infoo ja osallistujat'!C66:Q86"
bed_range = "'Infoo ja osallistujat'!C110:G127"
score_range = "'Infoo ja osallistujat'!AI46:AO63"



def signup_is_live():
    current_time = datetime.now()
    target_time = datetime(2023, 5, 15, 17, 15, 0)
    return current_time > target_time

def payment_is_live():
    current_time = datetime.now()
    target_time = datetime(2023, 6, 3, 12, 0, 0)
    return current_time > target_time

def mokki_is_live():
    current_time = datetime.now()
    target_time = datetime(2023, 6, 29, 16, 0, 0)
    return current_time > target_time

def find_index_of_name(list_of_lists, name):
    for index, sublist in enumerate(list_of_lists):
        if sublist[0] == name:
            return index
    return -1  

def time_remaining():
    current_time = datetime.now()
    mokki_time = datetime(2023, 6, 29, 16, 0, 0)
    remaining_time = mokki_time - current_time

    # Extract days, hours, minutes, and seconds from the remaining time
    days = remaining_time.days
    hours, remainder = divmod(remaining_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Construct the string with the remaining time
    time_string = f"Mökkiin aikaa: {days} päivää, {hours} tuntia, {minutes} minuuttia, ja {seconds} sekunttia"
    return time_string

def find_player(players, name):
    for player in players:
        if player['name'].lower() == name.lower().strip('<>'):
            return player
    return -1  

def get_players():
    try:
        response = requests.get("https://api.frisbeer.win/API/players/")
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        return response.json()  # Return the response content parsed as JSON
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

def create_fair_games(players, numb_games):

    # Generate all possible combinations of two teams
    shuffle(players)
    team_combinations = itertools.combinations(players, 3)
    ready_teams = []
    for i in range(numb_games):
        min_score_difference = 5000
        fair_teams = None
        # Find the combination with minimum score difference
        for team in team_combinations:
            team1 = team
            rest_of_players = [p for p in players if p not in team1]
            team_combinations2 = itertools.combinations(rest_of_players, 3)
            for team2 in team_combinations2:
                team1_average_score = sum(player["score"] for player in team1) / 3
                team2_average_score = sum(player["score"] for player in team2) / 3

                score_difference = abs(team1_average_score - team2_average_score)
                if score_difference < min_score_difference:
                    min_score_difference = score_difference
                    fair_teams = (team1, team2)
        team1_average_score = sum(player["score"] for player in fair_teams[0]) / 3
        team2_average_score = sum(player["score"] for player in fair_teams[1]) / 3

        score_difference = abs(team1_average_score - team2_average_score)
        ready_teams.append(fair_teams)
        players = [p for p in players if p not in fair_teams[0] and p not in fair_teams[1]]
        if len(rest_of_players) < 6:
            return ready_teams
        team_combinations = itertools.combinations(players, 3)
    return ready_teams

def create_random_games(players, numb_games):
    shuffle(players)
    result = []
    for i in range(numb_games):
        if len(players) < 6:
            break
        team1 = [players.pop(0), players.pop(0), players.pop(0)]
        team2 = [players.pop(0), players.pop(0), players.pop(0)]
        result.append((team1, team2))
    return result

def get_teams_string(games):
    result_string = ""
    for game in games:
        team1 = game[0]
        team2 = game[1]
        team1_average_score = round(sum(player["score"] for player in team1) / 3)
        team2_average_score = round(sum(player["score"] for player in team2) / 3)

        result_string += f"{team1[0]['name']}, {team1[1]['name']}, {team1[2]['name']}\n ({team1_average_score}) --vs-- ({team2_average_score})\n{team2[0]['name']}, {team2[1]['name']}, {team2[2]['name']}\n\n"
    return result_string



async def mokki_ilmo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if(signup_is_live() != True):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ilmo ei ole auki. Palaa asiaan 15.5 klo 17:15")    
    elif(len(args) < 1):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Kerro kuka olet '/mokille <mökkeilijän nimi>'")
    elif(update.message.chat.type != 'private'):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Pistätkö yksityisviestiä")
    else:
        keyboard = [[InlineKeyboardButton("Kyllä", callback_data='kylla'),
                 InlineKeyboardButton("Ei", callback_data='ei')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['user_param'] = args
        await update.message.reply_text("Haluatko varmasti lähteä mökille? Ilmoittautuminen on sitovaa", reply_markup=reply_markup)

async def mokki_alkaa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if mokki_is_live() is False:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=time_remaining())    
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Mökkiin aikaa: Mökki on jo, miksi kyselet etkä pelaa")

async def maksettu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if(payment_is_live() != True):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Maksu ei ole auki. Palaa asiaan 3.6 klo 12:00")
        return
    if(len(args) < 1):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Kerro kuka olet '/maksettu <mökkeilijän nimi>'")
        return
    signups = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
    names = signups.get('values', [])
    names = [cell for cell in names if cell]
    names_only = [cell[0] for cell in names if cell]
    name = ' '.join(args)
    if name not in names_only:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="'{}' ei ole ilmonnut mökille".format(name))
        return

    sleeps = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=bed_range
        ).execute()
    beds = sleeps.get('values', [])
    beds = [cell for cell in beds if cell]
    bed_names_only = [cell[0] for cell in beds if cell]
    index = find_index_of_name(names, name)
    if name in bed_names_only:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="'{}' on jo maksanut".format(name))
        return
    bed_count = len(bed_names_only)
    beds.append([name])
    request_body = {
        'values': beds
    }
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=bed_range,
        valueInputOption='USER_ENTERED',
        body=request_body
    ).execute()
    if(index > -1):
        names[index][7] = 'kyllä'
        request_body = {
            'values': names
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=request_body
        ).execute()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Kiitos maksusta. {} nukkuu sijalla {}".format(name, bed_count + 1))

async def sijoitukset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    signups = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=score_range
        ).execute()
    names = signups.get('values', [])
    names = [cell for cell in names if cell]
    names_only = [cell[0] for cell in names if cell]
    players = get_players()
    result = []
    for index, name in enumerate(names_only):
        player = find_player(players, name)
        original = 0
        try:
            original = int(names[index][5])
        except ValueError:
            pass
        if player == -1:
            result.append({'name': name, 'score': 'ei löytynyt', 'change': original * - 1})
        else:
            player['change'] = player['score'] - original
            result.append(player)
    result = sorted(result, key=lambda x: x['change'], reverse=True)
    return_text = ''
    for index, player in enumerate(result):
        return_text += '{}. {} - {} ({})\n'.format(index + 1, player['name'], player['score'], player['change'])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=return_text)

async def create_teams(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    numb_teams = 3
    if len(args) > 0:
        try:
            numb_teams = int(args[0])
            if numb_teams < 1 or numb_teams > 3:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Ensimmäisen argumentin pitää olla numero 1|2|3")
                return    
        except ValueError:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Ensimmäisen argumentin pitää olla numero 1|2|3")
            return
    if len(args) == 2 and args[1] != "rand":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="toinen argumentti voi olla 'rand' randomeille tiimeille")
        return
    signups = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=score_range
        ).execute()
    names = signups.get('values', [])
    names = [cell for cell in names if cell]
    names_only = [cell[0] for cell in names if cell]
    players = get_players()
    result = []
    for index, name in enumerate(names_only):
        player = find_player(players, name)
        original = 0
        try:
            original = int(names[index][5])
        except ValueError:
            pass
        if player == -1:
            result.append({'name': name, 'score': 0})
        else:
            result.append(player)
    if len(args) == 2:
        games = create_random_games(result, numb_teams)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=get_teams_string(games))
    else:
        games = create_fair_games(result, numb_teams)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=get_teams_string(games))
    # await context.bot.send_message(chat_id=update.effective_chat.id, text=return_text)
            

async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_param = context.user_data.get('user_param')
    name = ' '.join(user_param)
    if query.data == 'kylla':
        # Make a request to read the data from the spreadsheet
        signups = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        names = signups.get('values', [])
        cells = len(names)
        names = [cell for cell in names if cell]
        for i in names:
            if len(i) < 15:
                i = i + [''] * (15 - len(i))
        names_only = [cell[0] for cell in names if cell]
        if name not in names_only:
            names.append([name])
        else:
            reply = name + ' on jo mokillä'
            await query.edit_message_text(text=reply)
            return
        for i in range(cells - len(names)):
            names.append(['', '', '', '', '', '', '', '', '', '', '', '', '', '', ''])
        request_body = {
            'values': names
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=request_body
        ).execute()
        response = 'Olet ilmoittautunut mökille ' + name
        await query.edit_message_text(text=response)
    elif query.data == 'ei':
        await query.edit_message_text(text="Ei sitten, ehkä ens kerralla")


        
if __name__ == '__main__':
    application = ApplicationBuilder().token(token).build()
    
    # mokki_handler = CommandHandler('mokille', mokki_ilmo)
    # mokki_reply_handler = CallbackQueryHandler(button)
    maksu_handler = CommandHandler('maksettu', maksettu)
    sijoitukset_handler = CommandHandler('sijoitukset', sijoitukset)
    aika_handler = CommandHandler('mokki', mokki_alkaa)
    tiimi_handler = CommandHandler('tiimit', create_teams)

    # application.add_handler(mokki_handler)
    # application.add_handler(mokki_reply_handler)
    application.add_handler(maksu_handler)
    application.add_handler(sijoitukset_handler)
    application.add_handler(aika_handler)
    application.add_handler(tiimi_handler)

    
    application.run_polling()
