from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)


BOT_TOKEN = "5980643111:AAGboEhnGpZ1rYsJl7i4W9NVg3XD8upuD0E"


WEB_APP_URL = "https://your-domain.com"


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    keyboard = [

        [

            InlineKeyboardButton(
                "🎬 Open AbayFlix",
                web_app=WebAppInfo(
                    url=WEB_APP_URL
                )
            )

        ]

    ]


    reply_markup = InlineKeyboardMarkup(
        keyboard
    )


    await update.message.reply_text(

        f"""
🎬 እንኳን ወደ AbayFlix በደህና መጡ!

👤 {user.first_name}

ምርጥ ፊልሞችን እና
ተከታታይ ፊልሞችን ይመልከቱ።

""",

        reply_markup=reply_markup

    )




async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        """
🎬 AbayFlix Help

/start - Open App

ከተጨማሪ አገልግሎት ጋር ይጠብቁ።
"""

    )





def main():

    app = Application.builder()\
    .token(BOT_TOKEN)\
    .build()



    app.add_handler(

        CommandHandler(
            "start",
            start
        )

    )


    app.add_handler(

        CommandHandler(
            "help",
            help_command
        )

    )



    print(
        "AbayFlix Bot Started..."
    )


    app.run_polling()




if __name__ == "__main__":

    main()