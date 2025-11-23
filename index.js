const { Telegraf } = require("telegraf");

const tokens = [
  "8470961208:AAGfEuFp8YYhDevvQTrAZKO3Bci60nygGno",
  "8516563029:AAEh_n_m8dQodpIwqrxfvfO-uQbqaM6c148",
  "7525940881:AAGLlOQEE8W1WmRiXtiUlPuzwpBgcMPGA4k",
  "8282249419:AAFmsoqmiR005ODtCiFoDiQeXjFZjxyYXfU",
  "8537687387:AAE4eSA-svj_JEyaR3ZEiJmbNlrrXVjvcd8",
  "8592926668:AAEJNY1JVcWzCi0_X4FbByh9zj6brkaPYec"
];

tokens.forEach((token, index) => {
  const bot = new Telegraf(token);

  bot.start((ctx) => ctx.reply(`BOT ${index + 1} đã chạy ✓`));

  bot.command("menu", (ctx) => {
    ctx.reply(`Menu của BOT ${index + 1}`);
  });

  bot.launch()
    .then(() => console.log(`BOT ${index + 1} ĐÃ CHẠY ✓`))
    .catch((err) => console.log(`BOT ${index + 1} LỖI TOKEN ❌`, err.message));
});

// Render không cần port — giữ tiến trình sống
setInterval(() => {}, 1000);
