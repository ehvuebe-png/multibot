const fs = require("fs");
const { Telegraf } = require("telegraf");
const { bots, admins } = require("./config");

// ===================== LOAD FILE WAR =====================
let warLines = [];
try {
    warLines = fs.readFileSync("war.txt", "utf8").split("\n").filter(x => x.trim());
} catch (e) {
    console.log("⚠ Chưa có war.txt hoặc lỗi đọc file!");
}

// ===================== KIỂM TRA ADMIN =====================
function isAdmin(id) {
    return admins.includes(String(id)); // so sánh dạng chuỗi để tránh lỗi
}

// ===================== KHỞI CHẠY MỖI BOT =====================
bots.forEach(botInfo => {

    const bot = new Telegraf(botInfo.token);

    // báo bot đang chạy
    bot.launch()
        .then(() => console.log(`${botInfo.name} ĐÃ CHẠY ✔`))
        .catch(err => console.log(`${botInfo.name} LỖI TOKEN ❌`, err));

    // ===================== MENU =====================
    const menuText = `
🔥 <b>MENU BOT</b>

• /random – gửi 1 dòng random trong war.txt
• /tag @user – tag 1 người + 1 dòng war.txt
• /menu – xem menu

<b>ADMIN:</b>
• /addadmin ID
• /deladmin ID
• /admins – xem danh sách admin
`;

    bot.command("menu", ctx => {
        if (!isAdmin(ctx.from.id)) 
            return ctx.reply("❌ Bạn không có quyền.");

        return ctx.reply(menuText, { parse_mode: "HTML" });
    });

    // ===================== RANDOM WAR =====================
    bot.command("random", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Bạn không có quyền.");

        let line = warLines[Math.floor(Math.random() * warLines.length)];
        ctx.reply(line);
    });

    // ===================== TAG + WAR =====================
    bot.hears(/\/tag (.+)/, ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Bạn không có quyền.");

        let user = ctx.match[1];  
        let line = warLines[Math.floor(Math.random() * warLines.length)];

        ctx.reply(`${user} ${line}`);
    });

    // ===================== THÊM ADMIN =====================
    bot.hears(/\/addadmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id)) 
            return ctx.reply("❌ Bạn không có quyền.");

        let newID = ctx.match[1];
        if (!admins.includes(newID)) admins.push(newID);

        ctx.reply(`✔ Đã thêm admin: ${newID}`);
    });

    // ===================== XOÁ ADMIN =====================
    bot.hears(/\/deladmin (\d+)/, ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Bạn không có quyền.");

        let removeID = ctx.match[1];
        let i = admins.indexOf(removeID);
        if (i !== -1) admins.splice(i, 1);

        ctx.reply(`✔ Đã xoá admin: ${removeID}`);
    });

    // ===================== XEM ADMIN =====================
    bot.command("admins", ctx => {
        if (!isAdmin(ctx.from.id))
            return ctx.reply("❌ Bạn không có quyền.");

        ctx.reply("📌 ADMIN LIST:\n" + admins.join("\n"));
    });

});
