const fs = require("fs");
const TelegramBot = require("node-telegram-bot-api");
const { admins, bots } = require("./config");

// ========== KIỂM TRA ADMIN ==========
function isAdmin(id) {
    return admins.includes(id);
}

// ========== KHỞI TẠO BOT ==========
function setupBot(botConfig) {
    const bot = new TelegramBot(botConfig.token, { polling: true });

    console.log("BOT ĐANG CHẠY:", botConfig.name);

    // ========== MENU ==========
    const menuText = `
🔥 <b>MENU BOT</b>

<b>LỆNH:</b>
• /menu – mở menu
• /random – gửi 1 dòng random từ war.txt
• /tag@username – tag 1 người + random war.txt

<b>ADMIN:</b>
• /addadmin ID – thêm admin
• /deladmin ID – xóa admin
• /admins – xem danh sách admin
`;

    bot.onText(/\/menu/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");
        bot.sendMessage(msg.chat.id, menuText, { parse_mode: "HTML" });
    });

    // ========== RANDOM WAR ==========
    bot.onText(/\/random/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        if (!fs.existsSync("war.txt"))
            return bot.sendMessage(msg.chat.id, "⚠ Không tìm thấy war.txt");

        const lines = fs.readFileSync("war.txt", "utf8").split("\n").filter(x => x.trim());
        if (lines.length === 0)
            return bot.sendMessage(msg.chat.id, "⚠ war.txt trống.");

        const text = lines[Math.floor(Math.random() * lines.length)];
        bot.sendMessage(msg.chat.id, text);
    });

    // ========== TAG USER ==========
    bot.onText(/\/tag@([A-Za-z0-9_]+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const username = match[1];

        if (!fs.existsSync("war.txt"))
            return bot.sendMessage(msg.chat.id, "⚠ Không tìm thấy war.txt");

        const lines = fs.readFileSync("war.txt", "utf8").split("\n").filter(x => x.trim());
        if (lines.length === 0)
            return bot.sendMessage(msg.chat.id, "⚠ war.txt trống.");

        const text = lines[Math.floor(Math.random() * lines.length)];

        bot.sendMessage(msg.chat.id, `@${username} ${text}`);
    });

    // ========== THÊM ADMIN ==========
    bot.onText(/\/addadmin (\d+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const id = Number(match[1]);
        if (admins.includes(id))
            return bot.sendMessage(msg.chat.id, "⚠ ID này đã là admin.");

        admins.push(id);
        fs.writeFileSync("./config.js", updateConfig());
        bot.sendMessage(msg.chat.id, `✅ Đã thêm admin: ${id}`);
    });

    // ========== XÓA ADMIN ==========
    bot.onText(/\/deladmin (\d+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const id = Number(match[1]);
        const i = admins.indexOf(id);

        if (i === -1)
            return bot.sendMessage(msg.chat.id, "⚠ ID không có trong admin.");

        admins.splice(i, 1);
        fs.writeFileSync("./config.js", updateConfig());
        bot.sendMessage(msg.chat.id, `🗑 Đã xóa admin: ${id}`);
    });

    // ========== XEM ADMIN ==========
    bot.onText(/\/admins/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

        const list = admins.join("\n");
        bot.sendMessage(msg.chat.id, `👑 <b>ADMIN LIST:</b>\n${list}`, {
            parse_mode: "HTML"
        });
    });

    return bot;
}

// ====== TỰ ĐỘNG CẬP NHẬT FILE CONFIG SAU KHI ADD/DEL ADMIN ======
function updateConfig() {
    return `
module.exports = {
    admins: [${admins.join(", ")}],
    bots: ${JSON.stringify(bots, null, 4)}
};
`;
}

// ====== CHẠY TOÀN BỘ BOT ======
bots.forEach(bot => setupBot(bot));
