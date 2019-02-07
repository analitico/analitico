import { Component, EventEmitter, Input, OnDestroy, Output, Inject, forwardRef, OnInit } from '@angular/core';
import { HttpClient, HttpEventType, HttpHeaders, HttpParams } from '@angular/common/http';
import { AoMatFileUploadQueueComponent } from 'src/app/components/ao-mat-file-upload-queue/ao-mat-file-upload-queue.component';

@Component({
    selector: 'app-ao-mat-file-upload',
    templateUrl: './ao-mat-file-upload.component.html',
    styleUrls: ['./ao-mat-file-upload.component.css']
})
export class AoMatFileUploadComponent implements OnInit, OnDestroy {



    public isUploading = false;



    /* Http request input bindings */
    @Input()
    httpUrl = 'http://localhost:8080';

    @Input()
    httpRequestHeaders: HttpHeaders | {
        [header: string]: string | string[];
    } = new HttpHeaders();

    @Input()
    httpRequestParams: HttpParams | {
        [param: string]: string | string[];
    } = new HttpParams();

    @Input()
    fileAlias = 'file';

    @Input()
    get file(): any {
        return this._file;
    }
    set file(file: any) {
        this._file = file;
        this.total = this._file.size;
    }

    @Input()
    set id(id: number) {
        this._id = id;
    }
    get id(): number {
        return this._id;
    }

    /** Output  */
    @Output() removeEvent = new EventEmitter<AoMatFileUploadComponent>();
    @Output() uploaded = new EventEmitter();

    public progressPercentage = 0;
    public loaded = 0;
    public total = 0;
    private _file: any;
    private _id: number;
    private fileUploadSubscription: any;


    constructor(
        private HttpClient: HttpClient
        , @Inject(forwardRef(() => AoMatFileUploadQueueComponent)) public matFileUploadQueue: AoMatFileUploadQueueComponent
    ) {

        if (matFileUploadQueue) {
            this.httpUrl = matFileUploadQueue.httpUrl || this.httpUrl;
            this.httpRequestHeaders = matFileUploadQueue.httpRequestHeaders || this.httpRequestHeaders;
            this.httpRequestParams = matFileUploadQueue.httpRequestParams || this.httpRequestParams;
            this.fileAlias = matFileUploadQueue.fileAlias || this.fileAlias;
        }

    }
    ngOnInit() {
        // start immediately
        this.upload();
    }

    // get a cookie from the page
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


    public upload(): void {
        if (this.isUploading) {
            // still doing...
            return;
        }
        this.isUploading = true;
        // How to set the alias?
        const formData = new FormData();
        formData.set(this.fileAlias, this._file, this._file.name);
        // check if we have a csrttoken
        const xToken = this.getCookie('csrftoken');
        if (xToken) {
            // add csfr token
            this.httpRequestHeaders = (<HttpHeaders>this.httpRequestHeaders).append('X-CSRFTOKEN', xToken);
        }
        this.fileUploadSubscription = this.HttpClient.post(this.httpUrl, formData, {
            headers: this.httpRequestHeaders,
            observe: 'events',
            params: this.httpRequestParams,
            reportProgress: true,
            responseType: 'json'
        }).subscribe((event: any) => {
            if (event.type === HttpEventType.UploadProgress) {
                // notify progess
                this.progressPercentage = Math.floor(event.loaded * 100 / event.total);
                this.loaded = event.loaded;
                this.total = event.total;
            } else if (event.type === HttpEventType.Response) {
                this.remove();
                this.uploaded.emit({ file: this._file, event: event });
                this.isUploading = false;
            }
        }, (error: any) => {
            if (this.fileUploadSubscription) {
                this.fileUploadSubscription.unsubscribe();
            }
            this.progressPercentage = 0;
            this.isUploading = false;
        });
    }

    remove(): void {
        console.log('remove');
        if (this.fileUploadSubscription) {
            this.fileUploadSubscription.unsubscribe();
        }
        this.removeEvent.emit(this);
    }

    ngOnDestroy() {
        console.log('file ' + this._file.name + ' destroyed...');
    }

}
