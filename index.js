const { Telegraf } = require("telegraf");
const fs = require("fs");
const config = require("./config");

function isAdmin(id) {
    return config.admins.includes(id);
}

function loadWarText() {
    return fs.readFileSync("war.txt", "utf8");
}

config.bots.forEach((botInfo, index) => {
    const bot = new Telegraf(botInfo.token);

    console.log(`${botInfo.name} đã khởi động`);

    bot.start((ctx) => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
        ctx.reply(`${botInfo.name} đã chạy ✓`);
    });

    bot.command("menu", (ctx) => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");

        ctx.reply(
`📌 MENU ${botInfo.name}

🧨 /spam <số lần>  
→ Spam nội dung từ war.txt  

🛑 /stop  
→ Dừng spam

👑 Admin:
- Thêm admin: Sửa file config.js
`
        );
    });

    let spamInterval = null;

    bot.command("spam", (ctx) => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
        
        const args = ctx.message.text.split(" ");
        const times = parseInt(args[1]);

        if (!times) return ctx.reply("⚠️ Sai cú pháp. Dùng: /spam 50");

        const text = loadWarText();

        let count = 0;

        spamInterval = setInterval(() => {
            ctx.reply(text);
            count++;
            if (count >= times) clearInterval(spamInterval);
        }, 300);
    });

    bot.command("stop", (ctx) => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
        clearInterval(spamInterval);
        ctx.reply("🛑 Đã dừng spam.");
    });

    bot.launch();
});
