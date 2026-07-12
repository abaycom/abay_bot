import sqlite3



DB = "abayflix.db"



def connect():

    return sqlite3.connect(DB)




def create_tables():

    con = connect()

    cur = con.cursor()


    # Users

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY,

        telegram_id INTEGER UNIQUE,

        username TEXT,

        first_name TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)



    # Favorites

    cur.execute("""
    CREATE TABLE IF NOT EXISTS favorites(

        id INTEGER PRIMARY KEY,

        telegram_id INTEGER,

        movie_id INTEGER,

        title TEXT,

        poster TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)



    # Watch History

    cur.execute("""
    CREATE TABLE IF NOT EXISTS history(

        id INTEGER PRIMARY KEY,

        telegram_id INTEGER,

        movie_id INTEGER,

        title TEXT,

        progress INTEGER DEFAULT 0,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)



    # VIP Ready

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vip(

        id INTEGER PRIMARY KEY,

        telegram_id INTEGER,

        status TEXT DEFAULT 'FREE',

        expire_date TEXT

    )
    """)



    con.commit()

    con.close()






def add_user(
    telegram_id,
    username,
    first_name
):

    con = connect()

    cur = con.cursor()


    cur.execute(
    """

    INSERT OR IGNORE INTO users
    (
    telegram_id,
    username,
    first_name
    )

    VALUES(?,?,?)

    """,

    (
    telegram_id,
    username,
    first_name
    )

    )


    con.commit()

    con.close()




def add_history(
    telegram_id,
    movie_id,
    title
):

    con = connect()

    cur = con.cursor()


    cur.execute(
    """

    INSERT INTO history
    (
    telegram_id,
    movie_id,
    title
    )

    VALUES(?,?,?)

    """,

    (
    telegram_id,
    movie_id,
    title
    )

    )


    con.commit()

    con.close()