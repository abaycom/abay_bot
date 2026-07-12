const tg = window.Telegram.WebApp;


tg.ready();

tg.expand();



let telegramUser = null;



if(tg.initDataUnsafe.user){


    telegramUser = tg.initDataUnsafe.user;


    console.log(
        "Telegram ID:",
        telegramUser.id
    );


    console.log(
        "Username:",
        telegramUser.username
    );


}else{


    console.log(
        "Not opened from Telegram"
    );


}