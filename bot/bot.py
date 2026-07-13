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

from database import (
    create_tables,
    add_user
)



BOT_TOKEN = "5980643111:AAElPXmXNdq7o0Vs-lcKZ9fFFG_BvxZzSj0"

WEB_APP_URL = "https://abaybot-production.up.railway.app"



async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user


    # Save User

    add_user(
        user.id,
        user.username,
        user.first_name
    )



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


    await update.message.reply_text(

        f"""
🎬 Welcome to AbayFlix

👤 {user.first_name}

ምርጥ ፊልሞችን እና
ተከታታይ ፊልሞችን ይመልከቱ.

""",

        reply_markup=
        InlineKeyboardMarkup(keyboard)

    )






# ADMIN

ADMIN_ID = 123456789




async def users_count(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):


    if update.effective_user.id != ADMIN_ID:

        return



    from database import connect


    con = connect()

    cur = con.cursor()


    cur.execute(
        "SELECT COUNT(*) FROM users"
    )


    count = cur.fetchone()[0]


    con.close()



    await update.message.reply_text(

        f"👥 Total Users: {count}"

    )







def main():

    create_tables()


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
            "users",
            users_count
        )

    )



    print(
        "AbayFlix Bot Running..."
    )


    app.run_polling()




if __name__=="__main__":

    main()