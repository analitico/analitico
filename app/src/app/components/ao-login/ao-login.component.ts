import { Component, OnInit } from '@angular/core';
import { AoGlobalStateStore } from 'src/app/services/ao-global-state-store/ao-global-state-store.service';

@Component({
    selector: 'app-ao-login',
    templateUrl: './ao-login.component.html',
    styleUrls: ['./ao-login.component.css']
})
export class AoLoginComponent implements OnInit {

    username: string;
    password: string;

    constructor(private globalState: AoGlobalStateStore) { }

    ngOnInit() {
    }

    login() {
        this.globalState.setProperty('user', { username: this.username });
    }
}
