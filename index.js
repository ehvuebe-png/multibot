const fs = require("fs");
const { Telegraf } = require("telegraf");
const { bots, admins } = require("./config");

// ===================== LOAD FILE WAR =====================
function loadWar() {
    try {
        return fs.readFileSync("war.txt", "utf8")
            .split("\n")
            .filter(x => x.trim());
    } catch {
        return [];
    }
}

// ===================== CHECK ADMIN =====================
function isAdmin(id) {
    return admins.includes(String(id));
}

// ===================== SPAM THREAD =====================
async function spamLoop(ctx, tag, fullMode, userList, bot) {
    if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

    bot.stopSpam[ctx.chat.id] = false;
    let war = loadWar();

    if (war.length === 0) return ctx.reply("⚠ war.txt rỗng!");

    ctx.reply(`🚀 BẮT ĐẦU SPAM\nTag: ${tag ? tag : "Không dùng tag"}\nMode: ${fullMode ? "FULL" : "1 dòng random"}`);

    while (!bot.stopSpam[ctx.chat.id]) {
        if (fullMode) {
            // Full war.txt
            for (let line of war) {
                if (bot.stopSpam[ctx.chat.id]) break;

                let msg = tag ? `${tag} ${line}` : line;
                await ctx.reply(msg);
                if (bot.delay > 0) await new Promise(r => setTimeout(r, bot.delay));
            }
        } else {
            // 1 dòng random loop
            let line = war[Math.floor(Math.random() * war.length)];
            let msg = tag ? `${tag} ${line}` : line;
            await ctx.reply(msg);
            if (bot.delay > 0) await new Promise(r => setTimeout(r, bot.delay));
        }
    }

    ctx.reply("🛑 ĐÃ DỪNG SPAM.");
}

// ===================== START ALL BOTS =====================
bots.forEach(botInfo => {

    const bot = new Telegraf(botInfo.token);

    bot.delay = 0;
    bot.stopSpam = {};

    bot.launch()
        .then(() => console.log(`${botInfo.name} RUN ✔`))
        .catch(err => console.log(`${botInfo.name} TOKEN ERROR ❌`, err));


    // ===================== MENU =====================
    bot.command("menu", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");

        ctx.reply(`
🔥 <b>MENU SPAM BOT</b>

📌 SPAM
• /spam – spam random war.txt (loop)
• /spamall – spam hết war.txt (loop)
• /spamtag @user – spam hết war.txt + tag user

⚙ CẤU HÌNH
• /setdelay X – đặt delay (ms)
• /stop – dừng spam

👑 ADMIN
• /admins – danh sách admin
• /addadmin ID
• /deladmin ID
`, { parse_mode: "HTML" });
    });


    // ===================== SET DELAY =====================
    bot.command("setdelay", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

        let parts = ctx.message.text.split(" ");
        if (!parts[1]) return ctx.reply("❌ Sai cú pháp: /setdelay 100");

        bot.delay = parseInt(parts[1]);
        ctx.reply(`⏱ Delay đặt thành: ${bot.delay}ms`);
    });


    // ===================== STOP =====================
    bot.command("stop", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");

        bot.stopSpam[ctx.chat.id] = true;
        ctx.reply("🛑 Đã gửi yêu cầu dừng spam.");
    });


    // ===================== SPAM RANDOM =====================
    bot.command("spam", ctx => {
        spamLoop(ctx, null, false, null, bot);
    });


    // ===================== SPAM FULL =====================
    bot.command("spamall", ctx => {
        spamLoop(ctx, null, true, null, bot);
    });


    // ===================== SPAM + TAG USER =====================
    bot.hears(/\/spamtag (@\S+)/, ctx => {
        let tag = ctx.match[1];
        spamLoop(ctx, tag, true, null, bot);
    });


    // ===================== ADMIN LIST =====================
    bot.command("admins", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
        ctx.reply("📌 ADMIN LIST:\n" + admins.join("\n"));
    });

    // ===================== ADD ADMIN =====================
    bot.hears(/\/addadmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
        let id = ctx.match[1];
        if (!admins.includes(id)) admins.push(id);
        ctx.reply(`✔ Đã thêm admin: ${id}`);
    });

    // ===================== DEL ADMIN =====================
    bot.hears(/\/deladmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
        let id = ctx.match[1];
        let index = admins.indexOf(id);
        if (index !== -1) admins.splice(index, 1);
        ctx.reply(`✔ Đã xoá admin: ${id}`);
    });

});
