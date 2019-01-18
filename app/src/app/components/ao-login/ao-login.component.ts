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

    constructor(private globalState: AoGlobalStateStore, private apiClient: AoApiClientService) { }

    ngOnInit() {
    }

    login() {
        this.apiClient.get('/author2')
        .then((data: any) => {
            console.log(data);
        })
        .catch((error: any) => {
            console.error('Login error');
        });
        this.globalState.setProperty('user', { username: this.username });
    }
}
