import { Component, OnInit, forwardRef, Inject } from '@angular/core';
import { MatFileUpload, MatFileUploadQueue } from 'angular-material-fileupload';
import { HttpClient, HttpEventType, HttpHeaders, HttpParams } from '@angular/common/http';

@Component({
    selector: 'app-ao-mat-file-upload',
    templateUrl: './ao-mat-file-upload.component.html',
    styleUrls: ['./ao-mat-file-upload.component.css']
})
export class AoMatFileUploadComponent extends MatFileUpload implements OnInit {

    constructor(httpClient: HttpClient,
        @Inject(forwardRef(() => MatFileUploadQueue)) public matFileUploadQueue: MatFileUploadQueue) {
        super(httpClient, matFileUploadQueue);
    }

    ngOnInit() {
    }

}
