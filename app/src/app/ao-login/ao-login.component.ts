import { Component, OnInit } from '@angular/core';

@Component({
  selector: 'app-ao-login',
  templateUrl: './ao-login.component.html',
  styleUrls: ['./ao-login.component.css']
})
export class AoLoginComponent implements OnInit {

  username: string;
  password: string;
  
  constructor() { }

  ngOnInit() {
  }

}
