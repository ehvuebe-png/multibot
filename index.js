const fs = require("fs");
const { Telegraf } = require("telegraf");
const config = require("./config");

function loadWarText() {
    if (fs.existsSync("war.txt")) {
        return fs.readFileSync("war.txt", "utf8");
    }
    return "Không tìm thấy file war.txt";
}

config.bots.forEach((botInfo, index) => {
    const bot = new Telegraf(botInfo.token);

    console.log(`${botInfo.name} (${botInfo.username}) đã khởi động...`);

    bot.start((ctx) => {
        ctx.reply(`✅ ${botInfo.name} đã chạy!`);
    });

    bot.command("id", (ctx) => {
        ctx.reply(`🆔 ID của bạn: ${ctx.from.id}`);
    });

    bot.command("menu", (ctx) => {
        if (!config.admins.includes(ctx.from.id)) {
            return ctx.reply("❌ Bạn không có quyền.");
        }

        ctx.reply(
`📌 MENU ĐIỀU KHIỂN ${botInfo.name}

1️⃣ /spam — Spam bằng file war.txt  
2️⃣ /stop — Dừng spam  
3️⃣ /id — Lấy ID Telegram  
4️⃣ Admin: ${config.admins.join(",")}

🔥 Bot: ${botInfo.username}`
        );
    });

    let spamInterval = null;

    bot.command("spam", (ctx) => {
        if (!config.admins.includes(ctx.from.id)) {
            return ctx.reply("❌ Bạn không có quyền.");
        }

        const text = loadWarText();

        ctx.reply("🚀 Bắt đầu spam...");

        spamInterval = setInterval(() => {
            ctx.reply(text);
        }, 500);
    });

    bot.command("stop", (ctx) => {
        if (!config.admins.includes(ctx.from.id)) {
            return ctx.reply("❌ Bạn không có quyền.");
        }

        clearInterval(spamInterval);
        ctx.reply("🛑 Đã dừng spam.");
    });

    bot.launch();
});
