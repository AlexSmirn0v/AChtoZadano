import './App.css';
import { Routes, Route } from 'react-router';
import HomeworkScreen from './components/HomeworkScreen';
import StartScreen from './components/StartScreen';
import React from 'react';

class App extends React.Component {
  constructor() {
    super();
    this.state = {url: ""};
  }
  
  componentDidMount() {
   this.setState({ url: process.env.REACT_APP_URL });
  }

  render () {
    return (
      <div className="App">
        <Routes>
          <Route path="/" element={<StartScreen url={this.state.url}/>}/>
          <Route path="/:grade" element={<HomeworkScreen url={this.state.url}/>}/>
          <Route path="/:grade/:sub" element={<SingleHomework url={this.state.url}/>}/>
          <Route path="/register" element={<UserRegScreen url={this.state.url}/>}/>
          <Route path="/login" element={<AdminLogScreen url={this.state.url}/>}/>
          <Route path="/new" element={<NewHWScreen url={this.state.url}/>}/>
          <Route path='/:grade/timetable' element={<TimetableScreen url={this.state.url}/>}/>
          <Route path='/:grade/info' element={<Information url={this.state.url}/>}/>
        </Routes>
      </div>
    );
  }
}

export default App;
