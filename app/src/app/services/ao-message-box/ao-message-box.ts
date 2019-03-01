import { MatDialog } from '@angular/material';
import { AoDialogComponent } from 'src/app/components/ao-dialog/ao-dialog.component';
import { Injectable } from '@angular/core';
@Injectable({
    providedIn: 'root',
})
export class AoMessageBoxService {
    constructor(private dialog: MatDialog) {}

    show(message, title = 'Alert',
        information = '', button = 0, allow_outside_click = false,
        style = 0, width = '500px') {
        const dialogRef = this.dialog.open(AoDialogComponent, {
            data: {
                title: title || 'Alert',
                message: message,
                information: information,
                button: button || 0,
                style: style || (title ? 1 : 0),
                allow_outside_click: allow_outside_click || false
            },
            width: width
        });
        return dialogRef.afterClosed();
    }
}

export enum MessageBoxButton {
    Ok = 0,
    OkCancel = 1,
    YesNo = 2,
    AcceptReject = 3
}

export enum MessageBoxStyle {
    Simple = 0,
    Full = 1
}
