import React from "react";
import { Button, Form } from "react-bootstrap";

export default class AdminLogScreen extends React.Component {
    constructor() {
        super();
        this.state = {
            login: "",
            password: "",
            remember_me: true
        };
    }
    submitForm() {
        const api_key = process.env.REACT_APP_API_KEY;
        fetch(`${this.props.url}/api/user/${this.state.login}/${api_key}`, {
            method: 'POST',
            body: JSON.stringify(this.state)
        })
    }
    render() {
        return (
            <Form onSubmit={this.submitForm}>
                <Form.Group className="mb-3" controlId="formGroupNick">
                    <Form.Label>Email address</Form.Label>
                    <Form.Control type="text" placeholder="Введите ваш ник в Telegram или логин, придуманный при регистрации" onChange={(e) => this.setState({ login: e.target.value} )}/>
                </Form.Group>
                <Form.Group className="mb-3" controlId="formGroupPassword">
                    <Form.Label>Password</Form.Label>
                    <Form.Control type="password" placeholder="Password" />
                </Form.Group>
                <Button variant="primary" type="submit">Войти</Button>
            </Form>
        )
    }
}