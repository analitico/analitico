/**
 * API HTTP REST Client to interact with the Api
 */
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { Injectable } from '@angular/core';

@Injectable({
    providedIn: 'root',
})

export class AoApiClientService {

    constructor(private http: HttpClient) { }

    get(url: string, options?: any): any {
        console.log('contacting ' + url);
        return new Promise((resolve, reject) => {
            this.http.get(environment.apiUrl + url, options)
                .subscribe(
                    response => {
                        this.parseResponse(response, resolve);
                    },
                    err => {
                        this.handleError(err, reject);
                    });
        });
    }

    private parseResponse(response: any, resolve: any): void {
        console.log(response);
        resolve(response);
    }

    private handleError(response: any, reject: any): void {
        let status = response.status;
        reject(response);
    }
}
