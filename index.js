const fs = require("fs");
const { Telegraf } = require("telegraf");
const { bots, admins } = require("./config");

// ===================== LOAD war.txt =====================
let warLines = [];
try {
    warLines = fs.readFileSync("war.txt", "utf8")
        .split("\n")
        .filter(x => x.trim());
} catch (e) {
    console.log("⚠ Lỗi đọc war.txt");
}

// ===================== CHECK ADMIN =====================
function isAdmin(id) {
    return admins.includes(String(id));
}

// ===================== RUN EACH BOT =====================
bots.forEach(botInfo => {

    const bot = new Telegraf(botInfo.token);

    bot.launch()
        .then(() => console.log(`✔ ${botInfo.name} ĐÃ CHẠY`))
        .catch(err => console.log(`❌ ${botInfo.name} LỖI TOKEN`, err));

    // ===================== MENU =====================
    const menuText = `
🔥 <b>MENU BOT (${botInfo.name})</b>

📌 LỆNH CHÍNH:
• /random – random 1 dòng war.txt
• /spam – spam toàn bộ war.txt
• /spamtag @user – spam toàn bộ war.txt kèm tag

👑 ADMIN:
• /addadmin ID
• /deladmin ID
• /admins – xem admin

📄 File đọc: war.txt
`;

    bot.command("menu", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");
        ctx.reply(menuText, { parse_mode: "HTML" });
    });

    // ===================== RANDOM =====================
    bot.command("random", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");

        let line = warLines[Math.floor(Math.random() * warLines.length)];
        ctx.reply(line);
    });

    // ===================== SPAM FULL war.txt =====================
    bot.command("spam", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");

        warLines.forEach(l => {
            ctx.reply(l).catch(() => {});
        });
    });

    // ===================== SPAMTAG FULL war.txt =====================
    bot.command("spamtag", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");

        let parts = ctx.message.text.split(" ");
        if (parts.length < 2 || !parts[1].startsWith("@"))
            return ctx.reply("❌ Sai cú pháp:\n/spamtag @user");

        let tag = parts[1];

        warLines.forEach(l => {
            ctx.reply(`${tag} ${l}`).catch(() => {});
        });
    });

    // ===================== ADD ADMIN =====================
    bot.command("addadmin", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");

        let parts = ctx.message.text.split(" ");
        if (parts.length < 2)
            return ctx.reply("❌ Sai cú pháp: /addadmin ID");

        let id = parts[1];
        if (!admins.includes(id)) admins.push(id);

        ctx.reply(`✔ Đã thêm admin: ${id}`);
    });

    // ===================== DEL ADMIN =====================
    bot.command("deladmin", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");

        let parts = ctx.message.text.split(" ");
        if (parts.length < 2)
            return ctx.reply("❌ Sai cú pháp: /deladmin ID");

        let id = parts[1];
        let idx = admins.indexOf(id);
        if (idx !== -1) admins.splice(idx, 1);

        ctx.reply(`✔ Đã xoá admin: ${id}`);
    });

    // ===================== ADMIN LIST =====================
    bot.command("admins", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Không có quyền.");
        ctx.reply("📌 ADMIN LIST:\n" + admins.join("\n"));
    });

});
