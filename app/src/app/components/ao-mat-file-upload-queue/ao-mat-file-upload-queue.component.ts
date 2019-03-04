/**
 * Displays a list of mat-upload components (upload queue)
 */
import { Component, OnDestroy, QueryList, Input, ContentChildren, forwardRef, AfterViewInit } from '@angular/core';
import { AoMatFileUploadComponent } from 'src/app/components/ao-mat-file-upload/ao-mat-file-upload.component';
import { Subscription, Observable, merge } from 'rxjs';
import { startWith } from 'rxjs/operators';
import { HttpHeaders, HttpParams } from '@angular/common/http';


/**
 * A material design file upload queue component.
 */
@Component({
    selector: 'app-ao-mat-file-upload-queue',
    templateUrl: './ao-mat-file-upload-queue.component.html',
    styleUrls: ['./ao-mat-file-upload-queue.component.css'],
    exportAs: 'matFileUploadQueue',
})
export class AoMatFileUploadQueueComponent implements OnDestroy, AfterViewInit {

    @ContentChildren(forwardRef(() => AoMatFileUploadComponent)) fileUploads: QueryList<AoMatFileUploadComponent>;

    /** Subscription to remove changes in files. */
    private _fileRemoveSubscription: Subscription | null;

    /** Subscription to changes in the files. */
    private _changeSubscription: Subscription;

    /** Combined stream of all of the file upload remove change events. */
    get fileUploadRemoveEvents(): Observable<AoMatFileUploadComponent> {
        return merge(...this.fileUploads.map(fileUpload => fileUpload.removeEvent));
    }

    public files: Array<any> = [];

    isVisible = false;

    ngAfterViewInit() {
        // When the list changes, re-subscribe
        this._changeSubscription = this.fileUploads.changes.pipe(startWith(null)).subscribe(() => {
            if (this._fileRemoveSubscription) {
                this._fileRemoveSubscription.unsubscribe();
            }
            this._listenTofileRemoved();
        });
    }

    private _listenTofileRemoved(): void {
        this._fileRemoveSubscription = this.fileUploadRemoveEvents.subscribe((event: AoMatFileUploadComponent) => {
            this.files.splice(event.id, 1);
            if (this.files.length === 0) {
                this.isVisible = false;
            }
        });
    }

    add(file: any, uploadUrl?: string, uploaded?: any) {
        this.files.push({file: file, uploadUrl: uploadUrl, uploaded: uploaded});
        this.isVisible = true;
    }

    public uploadAll() {
        this.fileUploads.forEach((fileUpload) => {
            fileUpload.upload();
        });
    }

    public removeAll() {
        this.files.splice(0, this.files.length);
        this.isVisible = false;
    }

    close() {
        this.isVisible = false;
    }

    ngOnDestroy() {
        if (this.files) {
            this.removeAll();
        }
    }

}
