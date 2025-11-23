const fs = require("fs");
const TelegramBot = require("node-telegram-bot-api");
const { admins, bots } = require("./config");

// ========== KIỂM TRA ADMIN ==========
function isAdmin(id) {
    return admins.includes(id);
}

function setupBot(botConfig) {
    const bot = new TelegramBot(botConfig.token, { polling: true });

    console.log("BOT ĐANG CHẠY:", botConfig.name);

    // MENU
    const menuText = `
🔥 <b>MENU BOT</b>

• /menu – mở menu
• /random – 1 dòng random từ war.txt
• /tag @user – tag + random war.txt

<b>ADMIN:</b>
• /addadmin ID
• /deladmin ID
• /admins
`;

    bot.onText(/\/menu/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        bot.sendMessage(msg.chat.id, menuText, { parse_mode: "HTML" });
    });

    // RANDOM WAR
    bot.onText(/\/random/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const lines = fs.readFileSync("war.txt", "utf8").split("\n").filter(t => t.trim());
        const text = lines[Math.floor(Math.random() * lines.length)];

        bot.sendMessage(msg.chat.id, text);
    });

    // TAG USER (HỖ TRỢ /tag @username)
    bot.onText(/\/tag\s+@([A-Za-z0-9_]+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const username = match[1];
        const lines = fs.readFileSync("war.txt", "utf8").split("\n").filter(t => t.trim());
        const text = lines[Math.floor(Math.random() * lines.length)];

        bot.sendMessage(msg.chat.id, `@${username} ${text}`, {
            parse_mode: "Markdown"
        });
    });

    // ADD ADMIN
    bot.onText(/\/addadmin (\d+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const id = Number(match[1]);
        if (admins.includes(id))
            return bot.sendMessage(msg.chat.id, "⚠ ID đã là admin.");

        admins.push(id);
        bot.sendMessage(msg.chat.id, `✅ Thêm admin: ${id}`);
    });

    // DELETE ADMIN
    bot.onText(/\/deladmin (\d+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const id = Number(match[1]);
        const i = admins.indexOf(id);

        if (i === -1)
            return bot.sendMessage(msg.chat.id, "⚠ ID không có trong admin.");

        admins.splice(i, 1);
        bot.sendMessage(msg.chat.id, `🗑 Xóa admin: ${id}`);
    });

    // ADMIN LIST
    bot.onText(/\/admins/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        bot.sendMessage(msg.chat.id, `👑 ADMIN LIST:\n${admins.join("\n")}`);
    });
}

bots.forEach(bot => setupBot(bot));
