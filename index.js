const TelegramBot = require("node-telegram-bot-api");
const fs = require("fs");

// ======================= CONFIG =========================
const TOKENS = [
    "8470961208:AAGfEuFp8YYhDevvQTrAZKO3Bci60nygGno",
    "8516563029:AAEh_n_m8dQodpIwqrxfvfO-uQbqaM6c148",
    "7525940881:AAGLlOQEE8W1WmRiXtiUlPuzwpBgcMPGA4k",
    "8282249419:AAFmsoqmiR005ODtCiFoDiQeXjFZjxyYXfU",
    "8537687387:AAE4eSA-svj_JEyaR3ZEiJmbNlrrXVjvcd8",
    "8592926668:AAEJNY1JVcWzCi0_X4FbByh9zj6brkaPYec"
];

const ADMIN_FILE = "admins.txt";
const WAR_FILE = "war.txt";

// ======================= LOAD ADMIN ======================
function loadAdmins() {
    if (!fs.existsSync(ADMIN_FILE)) fs.writeFileSync(ADMIN_FILE, "");
    return fs.readFileSync(ADMIN_FILE, "utf8")
             .split("\n")
             .filter(x => x.trim() !== "")
             .map(x => Number(x));
}

function isAdmin(uid) {
    return loadAdmins().includes(uid);
}

// ======================= LOAD war.txt ====================
function getRandomLine() {
    if (!fs.existsSync(WAR_FILE)) return null;
    const list = fs.readFileSync(WAR_FILE, "utf8")
                   .split("\n")
                   .filter(x => x.trim() !== "");
    if (list.length === 0) return null;
    return list[Math.floor(Math.random() * list.length)];
}

// ======================= CREATE MULTI BOT ================
TOKENS.forEach((token) => {

    const bot = new TelegramBot(token, { polling: true });

    console.log("BOT ĐANG CHẠY:", token.slice(0, 10));

    // ======================= MENU ============================
    const menuText = `
<b>🔥 MENU BOT</b>
// ======================= LỆNH /tag@user ========================
bot.onText(/\/tag@([A-Za-z0-9_]+)/, (msg, match) => {
    if (!isAdmin(msg.from.id))
        return bot.sendMessage(msg.chat.id, "⛔ Bạn không có quyền.");

    const username = match[1];
    const fs = require("fs");

    if (!fs.existsSync("war.txt"))
        return bot.sendMessage(msg.chat.id, "⚠ Không tìm thấy file war.txt");

    const lines = fs.readFileSync("war.txt", "utf8")
        .split("\n")
        .filter(x => x.trim() !== "");

    if (lines.length === 0)
        return bot.sendMessage(msg.chat.id, "⚠ war.txt trống.");

    const randomLine = lines[Math.floor(Math.random() * lines.length)];

    bot.sendMessage(msg.chat.id, `@${username} ${randomLine}`);
});
• /random – gửi 1 dòng random từ war.txt
• /tag @user – gửi 1 dòng war.txt kèm tag

<b>ADMIN:</b>
• /addadmin ID
• /deladmin ID
• /admins – xem danh sách admin
`;

    bot.onText(/\/menu/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "⛔ Bạn không có quyền");

        bot.sendMessage(msg.chat.id, menuText, { parse_mode: "HTML" });
    });

    // ======================= RANDOM ==========================
    bot.onText(/\/random/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "⛔ Bạn không có quyền");

        const line = getRandomLine();
        if (!line) return bot.sendMessage(msg.chat.id, "⚠ war.txt trống");

        bot.sendMessage(msg.chat.id, line);
    });

    // ======================= TAG USER =========================
    bot.onText(/\/tag (.+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "⛔ Bạn không có quyền");

        const user = match[1];
        const line = getRandomLine();

        if (!user.startsWith("@"))
            return bot.sendMessage(msg.chat.id, "❌ Username phải bắt đầu '@'");

        if (!line)
            return bot.sendMessage(msg.chat.id, "⚠ war.txt trống");

        bot.sendMessage(msg.chat.id, `${user} ${line}`);
    });

    // ======================= ADMIN SYSTEM =====================
    bot.onText(/\/addadmin (\d+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "⛔ Chỉ admin");

        const id = match[1];
        fs.appendFileSync(ADMIN_FILE, id + "\n");
        bot.sendMessage(msg.chat.id, `✅ Đã thêm admin: ${id}`);
    });

    bot.onText(/\/deladmin (\d+)/, (msg, match) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "⛔ Chỉ admin");

        const id = match[1];
        const list = loadAdmins().filter(x => x != id);
        fs.writeFileSync(ADMIN_FILE, list.join("\n") + "\n");
        bot.sendMessage(msg.chat.id, `❌ Đã xoá admin: ${id}`);
    });

    bot.onText(/\/admins/, (msg) => {
        if (!isAdmin(msg.from.id))
            return bot.sendMessage(msg.chat.id, "⛔ Không có quyền");

        bot.sendMessage(msg.chat.id, "<b>Danh sách admin:</b>\n" +
            loadAdmins().join("\n"),
            { parse_mode: "HTML" }
        );
    });

});
