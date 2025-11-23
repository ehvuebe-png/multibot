const ADMIN = [8062864886]; // ID admin chính

function isAdmin(id) {
    return ADMIN.includes(id);
}

module.exports = {
    admins: ADMIN,

    bots: [
        {
            username: "@Concacditcu_bot",
            token: "8470961208:AAGfEuFp8YYhDevvQTrAZKO3Bci60nygGno",
            name: "BOT 1"
        },
        {
            username: "@Concacmem_bot",
            token: "8592926668:AAEJNY1JVcWzCi0_X4FbByh9zj6brkaPYec",
            name: "BOT 2"
        },
        {
            username: "@Anhthien_bot",
            token: "8516563029:AAEh_n_m8dQodpIwqrxfvfO-uQbqaM6c148",
            name: "BOT 3"
        },
        {
            username: "@Anhthien_bot",
            token: "8537687387:AAE4eSA-svj_JEyaR3ZEiJmbNlrrXVjvcd8",
            name: "BOT 4"
        },
        {
            username: "@Igigulc_bot",
            token: "7525940881:AAGLlOQEE8W1WmRiXtiUlPuzwpBgcMPGA4k",
            name: "BOT 5"
        },
        {
            username: "@Gvfyhv_bot",
            token: "8282249419:AAFmsoqmiR005ODtCiFoDiQeXjFZjxyYXfU",
            name: "BOT 6"
        }
    ]
};
