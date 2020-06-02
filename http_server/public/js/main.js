document.addEventListener("DOMContentLoaded", () => {
    var app = new Vue({
        el: '#app',
        data: {
            user: null
        },
        methods: {
            set_user: function(user) {
                this.user = user;
            }
        }
    })
})

