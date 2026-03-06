require('dotenv').config();
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { Telegraf, Markup } = require('telegraf');

// --- 1. SETUP ---
const app = express();
const server = http.createServer(app);
const io = new Server(server, {
    cors: { origin: "*" } // ማንኛውም ድረ-ገጽ እንዲያገኘው
});

const BOT_TOKEN = process.env.BOT_TOKEN;
const ADMIN_ID = process.env.ADMIN_ID;
const bot = new Telegraf(BOT_TOKEN);

let timeLeft = 90; // 1:30 ደቂቃ ለውርርድ
let status = "BETTING";
let currentBets = [];
let balanceDatabase = {}; // ለሙከራ (በኋላ በ MongoDB ይተካል)

// --- 2. የጨዋታ ዑደት (GAME LOOP) ---
setInterval(() => {
    timeLeft--;

    if (timeLeft <= 0) {
        if (status === "BETTING") {
            status = "DRAWING";
            timeLeft = 30; // እጣው የሚወጣበት 30 ሰከንድ
            generateAndSendDraw();
        } else {
            status = "BETTING";
            timeLeft = 90;
            currentBets = []; // አዲስ ጨዋታ ሲጀመር ውርርድን አጽዳ
        }
    }

    // ለሁሉም ተጫዋቾች መረጃውን መላክ
    io.emit('gameUpdate', {
        timer: formatTime(timeLeft),
        status: status
    });
}, 1000);

function formatTime(s) {
    return Math.floor(s / 60).toString().padStart(2, '0') + ":" + (s % 60).toString().padStart(2, '0');
}

// እጣውን ማውጣት
function generateAndSendDraw() {
    const winningNumbers = [];
    while (winningNumbers.length < 20) {
        let n = Math.floor(Math.random() * 80) + 1;
        if (!winningNumbers.includes(n)) winningNumbers.push(n);
    }
    
    io.emit('drawResult', winningNumbers);
    calculatePayouts(winningNumbers);
}

// የገንዘብ ክፍያ (70/30 Logic)
function calculatePayouts(winningNumbers) {
    if (currentBets.length === 0) return;

    let totalPool = currentBets.reduce((sum, b) => sum + parseFloat(b.amount), 0);
    let prizePool = totalPool * 0.70; // 70% ለተሸላሚዎች

    let results = currentBets.map(bet => {
        let hits = bet.numbers.filter(n => winningNumbers.includes(n)).length;
        return { ...bet, hits };
    });

    results.sort((a, b) => b.hits - a.hits);
    let winnerCount = Math.max(1, Math.ceil(results.length * 0.15)); // 15% አሸናፊዎች
    let winners = results.slice(0, winnerCount);

    let totalWinnerWeights = winners.reduce((sum, w) => sum + (w.amount * w.hits), 0);

    winners.forEach(w => {
        if (w.hits > 0) {
            let winAmount = ( (w.amount * w.hits) / totalWinnerWeights ) * prizePool;
            balanceDatabase[w.userId] = (balanceDatabase[w.userId] || 0) + winAmount;
            bot.telegram.sendMessage(w.userId, `እንኳን ደስ አለዎት! ${w.hits} ቁጥር በመምታት ${winAmount.toFixed(2)} ETB አሸንፈዋል።`);
        }
    });
}

// --- 3. SOCKET.IO (ከ WEB APP ጋር ግንኙነት) ---
io.on('connection', (socket) => {
    console.log('አዲስ ተጫዋች ገብቷል');

    socket.on('placeBet', (data) => {
        const userBalance = balanceDatabase[data.userId] || 0;
        if (userBalance >= data.amount && status === "BETTING") {
            balanceDatabase[data.userId] -= data.amount;
            currentBets.push(data);
            socket.emit('betSuccess', { newBalance: balanceDatabase[data.userId] });
        } else {
            socket.emit('error', 'ባላንስ የለም ወይም ውርርድ ተዘግቷል');
        }
    });
});

// --- 4. TELEGRAM BOT (DEPOSIT/ADMIN) ---
bot.start((ctx) => ctx.reply('እንኳን ወደ Keno Bot መጡ! ለመጫወት Deposit ያድርጉ።'));

// ተጫዋች የቴሌብር ደረሰኝ ሲልክ
bot.on('photo', (ctx) => {
    const photoId = ctx.message.photo[ctx.message.photo.length - 1].file_id;
    bot.telegram.sendPhoto(ADMIN_ID, photoId, {
        caption: `ተቀማጭ ጥያቄ ከ: ${ctx.from.first_name}\nID: ${ctx.from.id}`,
        ...Markup.inlineKeyboard([
            [Markup.button.callback('100 ETB አጽድቅ', `approve_${ctx.from.id}_100`)],
            [Markup.button.callback('500 ETB አጽድቅ', `approve_${ctx.from.id}_500`)],
            [Markup.button.callback('ሰርዝ', `reject_${ctx.from.id}`)]
        ])
    });
    ctx.reply('ደረሰኝዎ ለአድሚን ተልኳል። ሲረጋገጥ ባላንስዎ ላይ ይጨመራል።');
});

// አድሚኑ ሲያጸድቅ
bot.action(/approve_(\d+)_(\d+)/, (ctx) => {
    const userId = ctx.match[1];
    const amount = parseInt(ctx.match[2]);
    balanceDatabase[userId] = (balanceDatabase[userId] || 0) + amount;
    bot.telegram.sendMessage(userId, `የ ${amount} ETB ተቀማጭዎ ጸድቋል! መልካም ዕድል!`);
    ctx.editMessageCaption(`✅ ${amount} ETB ለተጫዋች ${userId} ጸድቋል።`);
});

bot.action(/reject_(\d+)/, (ctx) => {
    const userId = ctx.match[1];
    bot.telegram.sendMessage(userId, `ደረሰኝዎ ተቀባይነት አላገኘም። እባክዎ በትክክል መላክዎን ያረጋግጡ።`);
    ctx.editMessageCaption(`❌ ተቀማጩ ተሰርዟል።`);
});

// --- 5. SERVER START ---
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`ሰርቨር በፖርት ${PORT} ላይ ስራ ጀምሯል`);
});

bot.launch();
