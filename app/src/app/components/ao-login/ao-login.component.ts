import { Component, OnInit } from '@angular/core';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';
import { AoApiClientService } from 'src/app/services/ao-api-client/ao-api-client.service';

@Component({
    selector: 'app-ao-login',
    templateUrl: './ao-login.component.html',
    styleUrls: ['./ao-login.component.css']
})
export class AoLoginComponent implements OnInit {

    username: string;
    password: string;
    CSRFToken: any;
    constructor(private globalState: AoGlobalStateStore, private apiClient: AoApiClientService) { }

    ngOnInit() {
       this.CSRFToken = this.getCookie('csrftoken');
    }


    getCookie(cname: string) {
        const name = cname + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return false;
    }

    login() {
        this.apiClient.post('/login', { username: this.username, password: this.password })
        .then((response: any) => {
            // notify to global state the user profile
            this.globalState.setProperty('user', response.data);
        })
        .catch((error: any) => {
            console.error('Login error');
        });
    }
}
