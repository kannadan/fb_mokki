
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, InlineQueryHandler, CallbackContext, CallbackQueryHandler
from datetime import datetime
from dotenv import load_dotenv

import os.path

from google.oauth2 import service_account
from googleapiclient.discovery import build

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



def signup_is_live():
    current_time = datetime.now()
    target_time = datetime(2023, 5, 12, 17, 0, 0)
    return current_time > target_time

async def mokki(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if(signup_is_live() != True):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Ilmo ei ole auki. Palaa asiaan 14.5 klo 17")    
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
        # response = ' '.join(args) + ' on menossa mökille'
        # await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

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
    
    mokki_handler = CommandHandler('mokille', mokki)
    mokki_reply_handler = CallbackQueryHandler(button)

    application.add_handler(mokki_handler)
    application.add_handler(mokki_reply_handler)

    
    application.run_polling()
