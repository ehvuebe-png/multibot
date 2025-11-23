// ==========================
// MULTI-BOT MAX SPEED SPAM
// ==========================

const fs = require("fs");
const { Telegraf } = require("telegraf");

// ========================= CONFIG =========================
const admins = ["8062864886"]; // ID admin của m

const bots = [
    { token: "8470961208:AAGfEuFp8YYhDevvQTrAZKO3Bci60nygGno", name: "BOT 1" },
    { token: "8592926668:AAEJNY1JVcWzCi0_X4FbByh9zj6brkaPYec", name: "BOT 2" },
    { token: "8516563029:AAEh_n_m8dQodpIwqrxfvfO-uQbqaM6c148", name: "BOT 3" },
    { token: "8537687387:AAE4eSA-svj_JEyaR3ZEiJmbNlrrXVjvcd8", name: "BOT 4" },
    { token: "7525940881:AAGLlOQEE8W1WmRiXtiUlPuzwpBgcMPGA4k", name: "BOT 5" },
    { token: "8282249419:AAFmsoqmiR005ODtCiFoDiQeXjFZjxyYXfU", name: "BOT 6" }
];

// ========================= LOAD WAR =========================
function loadWar() {
    try {
        return fs.readFileSync("war.txt", "utf8").split("\n").filter(x => x.trim());
    } catch {
        return [];
    }
}

// ========================= CHECK ADMIN =========================
function isAdmin(id) {
    return admins.includes(String(id));
}

// ========================= SPAM CORE (MAX SPEED) =========================
async function spamLoop(ctx, tag, mode, bot) {
    if (!isAdmin(ctx.from.id))
        return ctx.reply("❌ Bạn không có quyền.");

    bot.stopSpam[ctx.chat.id] = false;
    const war = loadWar();

    if (war.length === 0) return ctx.reply("⚠ war.txt trống.");

    ctx.reply(`🚀 BẮT ĐẦU SPAM MAX SPEED\nMode: ${mode}\nTag: ${tag ?? "Không dùng"}`);

    while (!bot.stopSpam[ctx.chat.id]) {

        if (mode === "all") {
            for (let line of war) {
                if (bot.stopSpam[ctx.chat.id]) break;

                let msg = tag ? `${tag} ${line}` : line;

                ctx.reply(msg).catch(() => {}); // bỏ lỗi flood
            }
        } else {
            let line = war[Math.floor(Math.random() * war.length)];
            let msg = tag ? `${tag} ${line}` : line;

            ctx.reply(msg).catch(() => {}); // bỏ lỗi flood
        }
    }

    ctx.reply("🛑 ĐÃ DỪNG SPAM.");
}

// ========================= KHỞI TẠO 6 BOT =========================
bots.forEach(info => {

    const bot = new Telegraf(info.token);
    bot.stopSpam = {};

    // BOT READY
    bot.launch()
        .then(() => console.log(`${info.name} ĐÃ CHẠY ✔`))
        .catch(err => console.log(`${info.name} TOKEN LỖI ❌`, err));

    // ========================= MENU =========================
    bot.command("menu", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Bạn không có quyền.");

        ctx.reply(`
🔥 MENU SPAM MAX SPEED

/spam – random 1 dòng MAX SPEED
/spamall – spam hết war.txt MAX SPEED
/spamtag @user – spam tag + war.txt MAX SPEED
/stop – dừng spam

📄 war.txt đang được đọc.
👑 Admin: ${admins.join(", ")}
        `);
    });

    // ========================= SPAM RANDOM =========================
    bot.command("spam", ctx => {
        spamLoop(ctx, null, "random", bot);
    });

    // ========================= SPAM ALL =========================
    bot.command("spamall", ctx => {
        spamLoop(ctx, null, "all", bot);
    });

    // ========================= SPAM TAG =========================
    bot.hears(/\/spamtag (.+)/, ctx => {
        let tag = ctx.match[1];
        spamLoop(ctx, tag, "all", bot);
    });

    // ========================= STOP =========================
    bot.command("stop", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");

        bot.stopSpam[ctx.chat.id] = true;
        ctx.reply("🛑 Đang dừng spam...");
    });

    // ========================= THÊM ADMIN =========================
    bot.hears(/\/addadmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
        let id = ctx.match[1];
        if (!admins.includes(id)) admins.push(id);
        ctx.reply(`✔ Đã thêm admin: ${id}`);
    });

    // ========================= XÓA ADMIN =========================
    bot.hears(/\/deladmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
        let id = ctx.match[1];
        let i = admins.indexOf(id);
        if (i !== -1) admins.splice(i, 1);
        ctx.reply(`✔ Đã xoá admin: ${id}`);
    });

    // ========================= LIST ADMIN =========================
    bot.command("admins", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Không có quyền.");
        ctx.reply("📌 ADMIN LIST:\n" + admins.join("\n"));
    });

});

// Keep alive
setInterval(() => {}, 1000);
