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

    post(url: string, body: any, options?: any): any {
        return new Promise((resolve, reject) => {
            this.http.post(environment.apiUrl + url, body, options)
                .subscribe(
                    response => {
                        this.parseResponse(response, resolve);
                    },
                    err => {
                        this.handleError(err, reject);
                    });
        });
    }

    put(url: string, body: any, options?: any): any {
        return new Promise((resolve, reject) => {
            this.http.put(environment.apiUrl + url, body, options)
                .subscribe(
                    response => {
                        this.parseResponse(response, resolve);
                    },
                    err => {
                        this.handleError(err, reject);
                    });
        });
    }

    delete(url: string, options?: any): any {
        return new Promise((resolve, reject) => {
            this.http.delete(environment.apiUrl + url, options)
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
        // console.log(response);
        resolve(response);
    }

    private handleError(response: any, reject: any): void {
        let status = response.status;
        // if (res.status === 401 || res.status === 403) {
        // if not authenticated
        reject(response);
    }
}
