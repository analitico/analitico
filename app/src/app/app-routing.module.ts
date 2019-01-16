import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { AoLoginComponent } from './ao-login/ao-login.component';

const routes: Routes = [
  { path: 'login', component: AoLoginComponent },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
