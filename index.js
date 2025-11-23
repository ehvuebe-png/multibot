const fs = require("fs");
const { Telegraf } = require("telegraf");
const { bots, admins } = require("./config");

// ===================== LOAD WAR FILE =====================
let warLines = [];
try {
    warLines = fs.readFileSync("war.txt", "utf8")
        .split("\n")
        .filter(x => x.trim());
} catch {
    console.log("⚠ war.txt không tồn tại!");
}

// ===================== CHECK ADMIN =====================
function isAdmin(id) {
    return admins.includes(String(id));
}

// ===================== START EACH BOT =====================
bots.forEach(info => {

    const bot = new Telegraf(info.token);

    bot.launch()
        .then(() => console.log(`${info.name} Đã chạy ✔`))
        .catch(e => console.log(`${info.name} LỖI TOKEN ❌`, e));

    // =============== MENU ===============
    const menu = `
🔥 <b>MENU BOT</b>

• /random — gửi 1 dòng war.txt
• /tag @user — tag + gửi war random
• /menu — xem menu

<b>ADMIN:</b>
• /addadmin ID
• /deladmin ID
• /admins — danh sách admin
`;

    bot.command("menu", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
        return ctx.reply(menu, { parse_mode: "HTML" });
    });

    // =============== RANDOM ===============
    bot.command("random", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
        let line = warLines[Math.floor(Math.random() * warLines.length)];
        ctx.reply(line);
    });

    // =============== TAG ===============
    bot.hears(/\/tag (.+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");

        let user = ctx.match[1];
        let line = warLines[Math.floor(Math.random() * warLines.length)];
        ctx.reply(`${user} ${line}`);
    });

    // =============== ADD ADMIN ===============
    bot.hears(/\/addadmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");

        let id = ctx.match[1];
        if (!admins.includes(id)) admins.push(id);

        ctx.reply(`✔ Đã thêm admin: ${id}`);
    });

    // =============== DELETE ADMIN ===============
    bot.hears(/\/deladmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");

        let id = ctx.match[1];
        let i = admins.indexOf(id);
        if (i !== -1) admins.splice(i, 1);

        ctx.reply(`✔ Đã xoá admin: ${id}`);
    });

    // =============== LIST ADMIN ===============
    bot.command("admins", ctx => {
        if (!isAdmin(ctx.from.id)) return ctx.reply("❌ Bạn không có quyền.");
        ctx.reply("📌 ADMIN LIST:\n" + admins.join("\n"));
    });
});
