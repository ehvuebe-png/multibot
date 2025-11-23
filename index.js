// ========== TAG USER ==========
bot.onText(/\/tag\s+@([A-Za-z0-9_]+)/, (msg, match) => {
    if (!isAdmin(msg.from.id))
        return bot.sendMessage(msg.chat.id, "❌ Bạn không có quyền.");

    const username = match[1];

    if (!fs.existsSync("war.txt"))
        return bot.sendMessage(msg.chat.id, "⚠ Không tìm thấy war.txt");

    const lines = fs.readFileSync("war.txt", "utf8").split("\n").filter(x => x.trim());
    if (lines.length === 0)
        return bot.sendMessage(msg.chat.id, "⚠ war.txt trống.");

    const text = lines[Math.floor(Math.random() * lines.length)];

    bot.sendMessage(msg.chat.id, `@${username} ${text}`, {
        parse_mode: "Markdown"
    });
});
