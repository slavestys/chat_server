let SYSTEM_MESSAGE_CODES = {
    USER_ONLINE: 1,
    USER_OFFLINE: 2,
    USER_JOINED: 3,
    USER_LEAVE: 4,
    COMMAND_SUCCESS: 5,
    AUTH_SUCCESS: 6
};

let chat_template =
`<div id="chat" v-if="chat_server_processor">   
    <div id="chat_title">Чат</div> 
    <div id="chat_middle">
        <div id="chat_left">            
            <div class="chat_room" v-bind:class="{chat_room_selected: current_room_id == room.id}" v-for="room in rooms" v-on:click="select_room(room.id)">
            {{room.name}}            
            </div>
        </div>
        <div id="chat_content">
            <div id="chat_messages">
                <p class="chat_message" 
                    v-bind:class="{chat_message_my: message.user_id === chat_server_processor.id}" 
                    v-for="message in room_messages"
                    v-on:click="edit_message_select(message)"
                >                    
                    <span class="chat_message_created_at">{{message.created_at_str}}</span>
                    <span class="chat_message_user">{{users_info[message.user_id].name}}:</span><br>
                    <span class="chat_message_content">{{message.message}}</span>
                </p>
            </div>            
             <textarea v-model="edit_message.text" v-if="current_room_id" v-on:keydown.ctrl.enter="send_message"></textarea>
        </div>        
    </div>   
</div>`;

Vue.component('chat', {
    props: ['user'],
    data: function () {
        return {
            rooms: {},
            current_room_id: null,
            edit_message: {
                id: null,
                text: ''
            },
            room_messages: [],
            chat_server_processor: null,
            socket: null,
            cmd_id: 1,
            users_info: {},
            waiting_commands: {}
        }
    },
    template: chat_template,
    created: function () {
        this.change_user(this.user);
    },
    watch: {
        user: function(val) {
            this.change_user(val);
        }
    },
    methods: {
        create_socket: function() {
            let socket = new WebSocket("ws://localhost:8765");
            this.socket = socket;

            socket.onopen = (e) => {
                this.socket = socket;
                this.send_command({command: 'auth_by_key', id: this.chat_server_processor.id, key: this.chat_server_processor.key});
            };
            console.log(this.socket);

            socket.onmessage = (event) => {
                let data = JSON.parse(event.data);
                if(data.command === 'system_message') {
                    this.process_system_message(data);
                }
                else if(data.command === 'message_info') {
                    this.process_message_info(data);
                }
            };

            socket.onclose = (event) => {
                if (event.wasClean) {
                    console.log(`[Чат] Соединение закрыто чисто, код=${event.code} причина=${event.reason}`);
                } else {
                    console.log(`[Чат] Соединение прервано, код=${event.code} причина=${event.reason}`);
                }
            };

            socket.onerror = function(error) {
                console.log(`[Чат] ${error.message}`);
            };
        },
        change_user: function(user) {
            this.chat_server_processor = user;
            if(this.chat_server_processor) {
                this.socket = this.create_socket();
            }
            else {
                if(this.socket) {
                    this.rooms = {};
                    this.current_room_id = null;
                    this.edit_message = '';
                    this.room_messages = [];
                    this.socket.close();
                    this.socket = null;
                    this.cmd_id = 1;
                    this.users_info = {};
                    this.waiting_commands = {};
                }
            }
        },
        process_auth_success: function(message) {
            let self = this;
            let room_id = null;
            message.rooms.forEach(function(room, i, rooms){
                if(!room_id) {
                    room_id = room.id;
                }
                self.rooms[room.id] = room;
            });
            message.users.forEach(function(user, i, users){
                self.users_info[user.id] = user;
            });
            self.select_room(room_id);
        },
        process_command_success: function(message) {
            let waiting_command = this.waiting_commands[message.cmd_id];
            if(!waiting_command) {
                return;
            }
            delete this.waiting_commands[message.cmd_id];
            if(waiting_command.type === 'message') {
                let messages = this.rooms[waiting_command.room_id].messages;
                this.delete_by_cmd_id(messages, message.cmd_id);
                this.insert_message(messages, message.data);
            }
        },
        process_system_message: function(message) {
            if(message.message_id === SYSTEM_MESSAGE_CODES.AUTH_SUCCESS) {
                this.process_auth_success(message);
            }
            else if(message.message_id === SYSTEM_MESSAGE_CODES.COMMAND_SUCCESS) {
                this.process_command_success(message);
            }
        },
        process_message_info: function(message) {
            this.insert_message(this.rooms[message.room_id].messages, message.message);
        },
        next_cmd_id: function() {
            let current_id = this.cmd_id;
            this.cmd_id++;
            return current_id
        },
        select_room: function(room_id) {
            if(this.current_room_id === room_id) {
                return
            }
            this.current_room_id = room_id;
            if(this.current_room_id) {
                this.room_messages = this.rooms[this.current_room_id].messages;
            }
        },
        edit_message_clear: function() {
            this.edit_message.id = null;
            this.edit_message.text = '';
        },
        edit_message_select: function(message) {
            if(message.user_id !== this.chat_server_processor.id) {
                return;
            }
            this.edit_message.id = message.id;
            this.edit_message.text = message.message;
        },
        send_message: function() {
            if(!this.edit_message.text) {
                return;
            }
            let msg;
            if(this.edit_message.id) {
                msg = {command: 'message_edit', 'id': this.edit_message.id, 'message': this.edit_message.text};
                let cmd_id = this.send_command(msg);
            }
            else {
                msg = {command: 'message', room_id: this.current_room_id, 'message': this.edit_message.text};
                let cmd_id = this.send_command(msg);
                let message = {message: this.edit_message.text, user_id: this.chat_server_processor.id, created_at: Math.round(Date.now() / 1000), cmd_id: cmd_id};
                this.insert_message(this.room_messages, message);
                this.waiting_commands[cmd_id] = {type: msg.command, room_id: this.current_room_id};
            }
            this.edit_message_clear();
        },
        insert_message: function(messages, message) {
            let index = -1;
            for(let i = messages.length - 1; i >= 0; i--) {
                if(message.created_at > messages[i].created_at) {
                    break;
                }
                else {
                    index = i;
                }
            }
            if(index >= 0) {
                messages.splice(index, 0, message);
            }
            else {
                messages.push(message);
            }
        },
        delete_by_cmd_id: function(messages, cmd_id) {
            let index = -1;
            for(let i = messages.length - 1; i >= 0; i--) {
                if(cmd_id === messages[i].cmd_id) {
                    index = i;
                    break;
                }
            }
            if(index >= 0) {
                messages.splice(index, 1);
            }
        },
        send_command: function(command) {
            command.cmd_id = this.next_cmd_id();
            let command_json = JSON.stringify(command);
            console.log(`send ${command_json}`);
            this.socket.send(command_json);
            return command.cmd_id;
        }
    }
});