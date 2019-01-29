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
        options = this.getDefaultOptions(options);
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
        options = this.getDefaultOptions(options);
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
        options = this.getDefaultOptions(options);
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

    patch(url: string, body: any, options?: any): any {
        options = this.getDefaultOptions(options);
        return new Promise((resolve, reject) => {
            this.http.patch(environment.apiUrl + url, body, options)
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
        options = this.getDefaultOptions(options);
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

    private getCookie(name: string) {
        const nameEQ = name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') {
                c = c.substring(1, c.length);
            }
            if (c.indexOf(nameEQ) === 0) {
                return c.substring(nameEQ.length, c.length);
            }
        }
        return null;
    }

    private getDefaultOptions(options) {
        if (typeof options === 'undefined' || options === null) {
            options = {};
        }
        options.withCredentials = true;
        if (typeof options.headers === 'undefined') {
            options.headers = {};
            if (typeof options.headers['Content-Type'] === 'undefined') {
                options.headers['Content-Type'] = 'application/json';
            }
            const xToken = this.getCookie('csrftoken');
            if (xToken) {
                options.headers['X-CSRFTOKEN'] = xToken;
            }
        }
        return options;
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
