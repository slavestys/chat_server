let template =
`<div id="login">    
    <template v-if="user">
        Привет {{user.name}}
        <button v-on:click="process_logout">Выход</button>
    </template>
    <template v-else>
        
        <form action="login" method="post" v-on:submit.prevent="process_login">
            <label>Вход:</label>
            <input type="text" v-model="login" v-on:keydown.enter.prevent="process_login">
            <input type="text" v-model="password" v-on:keydown.enter.prevent="process_login">            
        </form>
    </template>
</div>`;

Vue.component('login', {
    props: ['user_data'],
    data: function () {
        return {
            login: 'test',
            password: '1',
            user: null
        }
    },
    template: template,
    created: function () {
        let user = this.user_data ? JSON.parse(this.user_data) : null;
        this.change_user(user);
    },
    methods: {
        process_login: function () {
            let self = this;
            axios.post('/session', {login: this.login, password: this.password}).then(function (response) {
                let data = response.data;
                if(data.status === 'ok') {
                    self.change_user(data.user);
                }
            })
        },
        process_logout: function() {
            let self = this;
            axios.delete('/session').then(function() {
                self.change_user(null);
            })
        },
        change_user: function(user) {
            this.user = user;
            this.$emit('user-changed', user);
        }
    }
});